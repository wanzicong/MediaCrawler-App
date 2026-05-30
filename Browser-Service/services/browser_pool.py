# -*- coding: utf-8 -*-
"""
Browser Pool Manager - 浏览器池管理器

管理多个 Chrome/Edge 浏览器实例的生命周期：
- 启动浏览器进程（CDP 模式）
- 分配可用调试端口
- 健康检查与自动恢复
- 实例回收与端口释放

端口范围: 9222 ~ 9321 (100 个)
池大小: 可配置，默认 5
"""

import asyncio
import logging
import os
import platform as sys_platform
import socket
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, List, Any

import httpx

logger = logging.getLogger("browser_pool")

# 配置常量
CDP_PORT_START = int(os.getenv("CDP_PORT_START", "9222"))
CDP_PORT_END = int(os.getenv("CDP_PORT_END", "9321"))
POOL_SIZE = int(os.getenv("BROWSER_POOL_SIZE", "5"))
BROWSER_LAUNCH_TIMEOUT = int(os.getenv("BROWSER_LAUNCH_TIMEOUT", "30"))
CUSTOM_BROWSER_PATH = os.getenv("CUSTOM_BROWSER_PATH", "")
HEADLESS_DEFAULT = os.getenv("HEADLESS", "false").lower() == "true"
BROWSER_DATA_DIR = os.getenv("BROWSER_DATA_DIR", os.path.join(os.getcwd(), "browser_data"))


@dataclass
class BrowserInstance:
    """浏览器实例元数据"""

    instance_id: str             # UUID
    debug_port: int              # CDP 调试端口
    pid: Optional[int] = None    # 浏览器进程 PID
    browser_path: str = ""       # 浏览器可执行文件路径
    browser_name: str = ""       # 浏览器名称
    headless: bool = False       # 是否无头模式
    user_data_dir: str = ""      # Cookie 持久化目录
    platform_name: str = ""      # 关联平台 (xhs/dy/ks/bili/wb/tieba/zhihu)
    process: Optional[subprocess.Popen] = None  # 进程对象
    status: str = "starting"     # starting/ready/unhealthy/stopped
    created_at: float = field(default_factory=time.time)
    last_health_check: float = field(default_factory=time.time)
    context_count: int = 0       # 当前 Playwright 连接数
    health_fail_count: int = 0   # 连续健康检查失败次数
    ws_url: str = ""             # CDP WebSocket URL


class BrowserPool:
    """
    浏览器池管理器 (单例模式)

    职责:
    1. 管理浏览器实例的完整生命周期
    2. 端口分配与回收
    3. 实例状态跟踪
    """

    _instance: Optional["BrowserPool"] = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self.system = sys_platform.system()
        self.instances: Dict[str, BrowserInstance] = {}
        self._write_lock = asyncio.Lock()

        # 确保数据目录存在
        os.makedirs(BROWSER_DATA_DIR, exist_ok=True)

        logger.info(
            f"[BrowserPool] Initialized: system={self.system}, "
            f"port_range={CDP_PORT_START}-{CDP_PORT_END}, pool_size={POOL_SIZE}"
        )

    # ==================== 浏览器检测 ====================

    def detect_browser_paths(self) -> List[str]:
        """
        检测系统中可用的 Chrome/Edge 浏览器路径
        复用自 Crawler-Service 的 browser_launcher.py 逻辑
        """
        paths = []

        if self.system == "Windows":
            possible_paths = [
                os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe"),
                os.path.expandvars(r"%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe"),
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome Beta\Application\chrome.exe"),
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome Dev\Application\chrome.exe"),
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome SxS\Application\chrome.exe"),
            ]
        elif self.system == "Darwin":
            possible_paths = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Google Chrome Beta.app/Contents/MacOS/Google Chrome Beta",
                "/Applications/Google Chrome Dev.app/Contents/MacOS/Google Chrome Dev",
                "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
                "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                "/Applications/Microsoft Edge Beta.app/Contents/MacOS/Microsoft Edge Beta",
                "/Applications/Microsoft Edge Dev.app/Contents/MacOS/Microsoft Edge Dev",
                "/Applications/Microsoft Edge Canary.app/Contents/MacOS/Microsoft Edge Canary",
            ]
        else:  # Linux
            possible_paths = [
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable",
                "/usr/bin/google-chrome-beta",
                "/usr/bin/google-chrome-unstable",
                "/usr/bin/chromium-browser",
                "/usr/bin/chromium",
                "/snap/bin/chromium",
                "/usr/bin/microsoft-edge",
                "/usr/bin/microsoft-edge-stable",
                "/usr/bin/microsoft-edge-beta",
                "/usr/bin/microsoft-edge-dev",
            ]

        for path in possible_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                paths.append(path)

        return paths

    def get_browser_name(self, browser_path: str) -> str:
        """从路径推断浏览器名称"""
        lower = browser_path.lower()
        if "edge" in lower or "msedge" in lower:
            return "Microsoft Edge"
        elif "chromium" in lower:
            return "Chromium"
        elif "chrome" in lower:
            return "Google Chrome"
        return "Unknown Browser"

    # ==================== 端口管理 ====================

    def find_available_port(self, start_port: int = CDP_PORT_START) -> int:
        """
        从 start_port 开始扫描，返回第一个可用端口（排除自身实例已占用的）
        """
        port = start_port
        while port <= CDP_PORT_END:
            # 先检查自身实例是否占用此端口
            already_used = False
            for inst in self.instances.values():
                if inst.debug_port == port and inst.status not in ("stopped",):
                    already_used = True
                    break
            if already_used:
                port += 1
                continue

            # 再检查系统层面端口是否被占用
            if self.is_port_in_use(port):
                port += 1
                continue

            # 最后尝试 bind 确认可用
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.bind(("0.0.0.0", port))
                    return port
            except OSError:
                port += 1

        raise RuntimeError(
            f"[BrowserPool] No available port found in range {start_port}-{CDP_PORT_END}"
        )

    def is_port_in_use(self, port: int) -> bool:
        """检查端口是否已被占用（包括我们的实例）"""
        # 先检查我们的实例
        for inst in self.instances.values():
            if inst.debug_port == port and inst.status not in ("stopped",):
                return True

        # 再检查系统层面
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                result = s.connect_ex(("localhost", port))
                return result == 0
        except OSError:
            return False

    # ==================== 浏览器启动 ====================

    def launch_browser(
        self,
        browser_path: str,
        debug_port: int,
        headless: bool = False,
        user_data_dir: Optional[str] = None,
    ) -> subprocess.Popen:
        """
        启动浏览器进程

        复用自 Crawler-Service 的 browser_launcher.py 逻辑
        """
        args = [
            browser_path,
            f"--remote-debugging-port={debug_port}",
            "--remote-debugging-address=0.0.0.0",  # 允许远程连接
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-features=TranslateUI",
            "--disable-ipc-flooding-protection",
            "--disable-hang-monitor",
            "--disable-prompt-on-repost",
            "--disable-sync",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            # 反检测参数
            "--disable-blink-features=AutomationControlled",
            "--exclude-switches=enable-automation",
            "--disable-infobars",
        ]

        if headless:
            args.extend([
                "--headless",
                "--disable-gpu",
                "--hide-scrollbars",
                "--mute-audio",
                "--disable-restore-session-state",
                "--disable-features=SessionRestore",
                "--disable-session-crashed-bubble",
                "--window-size=1920,1080",
            ])
        else:
            args.extend([
                "--start-maximized",
            ])

        if user_data_dir:
            args.append(f"--user-data-dir={user_data_dir}")

        logger.info(f"[BrowserPool] Launching: {browser_path}")
        logger.info(f"[BrowserPool] Debug port: {debug_port}, headless: {headless}")
        if user_data_dir:
            logger.info(f"[BrowserPool] User data dir: {user_data_dir}")

        try:
            if self.system == "Windows":
                process = subprocess.Popen(
                    args,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                )
            else:
                process = subprocess.Popen(
                    args,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    preexec_fn=os.setsid,
                )

            return process

        except Exception as e:
            logger.error(f"[BrowserPool] Failed to launch browser: {e}")
            raise

    async def wait_for_browser_ready(self, debug_port: int, timeout: int = BROWSER_LAUNCH_TIMEOUT) -> bool:
        """
        等待浏览器就绪：先 socket connect，再 HTTP GET /json/version 验证 CDP 可用
        """
        logger.info(f"[BrowserPool] Waiting for browser on port {debug_port} (timeout={timeout}s)...")

        start_time = time.time()

        # 第一步：等待 socket 可连接
        while time.time() - start_time < timeout:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    result = s.connect_ex(("localhost", debug_port))
                    if result == 0:
                        break
            except Exception:
                pass
            await asyncio.sleep(0.5)
        else:
            logger.error(f"[BrowserPool] Browser socket not reachable on port {debug_port} after {timeout}s")
            return False

        # 第二步：验证 CDP HTTP 接口可用
        remaining = timeout - (time.time() - start_time)
        if remaining <= 0:
            remaining = 5

        async with httpx.AsyncClient() as client:
            poll_start = time.time()
            while time.time() - poll_start < remaining:
                try:
                    resp = await client.get(
                        f"http://localhost:{debug_port}/json/version",
                        timeout=5,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        ws_url = data.get("webSocketDebuggerUrl", "")
                        logger.info(f"[BrowserPool] Browser ready on port {debug_port}, CDP OK")
                        logger.debug(f"[BrowserPool] WebSocket URL: {ws_url}")
                        return True
                except Exception:
                    pass
                await asyncio.sleep(0.5)

        logger.error(f"[BrowserPool] CDP /json/version not responding on port {debug_port}")
        return False

    # ==================== 实例管理 ====================

    async def create_instance(
        self,
        headless: bool = HEADLESS_DEFAULT,
        platform: str = "",
        user_data_dir: Optional[str] = None,
    ) -> BrowserInstance:
        """
        创建新的浏览器实例

        Args:
            headless: 是否无头模式
            platform: 平台标识 (xhs/dy/ks/bili/wb/tieba/zhihu)
            user_data_dir: 用户数据目录（Cookie 持久化），为空时自动生成

        Returns:
            BrowserInstance: 新创建的浏览器实例
        """
        async with self._write_lock:
            # 1. 检测浏览器路径
            if CUSTOM_BROWSER_PATH and os.path.isfile(CUSTOM_BROWSER_PATH):
                browser_path = CUSTOM_BROWSER_PATH
            else:
                paths = self.detect_browser_paths()
                if not paths:
                    raise RuntimeError(
                        "No Chrome/Edge browser found. "
                        "Please install Chrome or set CUSTOM_BROWSER_PATH env variable."
                    )
                browser_path = paths[0]

            browser_name = self.get_browser_name(browser_path)

            # 2. 查找可用端口
            debug_port = self.find_available_port()
            logger.info(f"[BrowserPool] Found available port: {debug_port}")

            # 3. 确定 user_data_dir
            if not user_data_dir:
                if platform:
                    dir_name = f"cdp_{platform}_chrome_data"
                else:
                    dir_name = f"cdp_generic_chrome_data"
                user_data_dir = os.path.join(BROWSER_DATA_DIR, dir_name)

            os.makedirs(user_data_dir, exist_ok=True)

            # 4. 创建实例元数据
            instance_id = str(uuid.uuid4())
            instance = BrowserInstance(
                instance_id=instance_id,
                debug_port=debug_port,
                browser_path=browser_path,
                browser_name=browser_name,
                headless=headless,
                user_data_dir=user_data_dir,
                platform_name=platform,
                status="starting",
            )

            self.instances[instance_id] = instance

            # 5. 启动浏览器进程
            instance.process = self.launch_browser(
                browser_path=browser_path,
                debug_port=debug_port,
                headless=headless,
                user_data_dir=user_data_dir,
            )
            instance.pid = instance.process.pid

            # 6. 等待就绪
            ready = await self.wait_for_browser_ready(debug_port)
            if not ready:
                instance.status = "unhealthy"
                logger.error(f"[BrowserPool] Instance {instance_id} failed to become ready")
                raise RuntimeError(
                    f"Browser instance {instance_id} failed to become ready "
                    f"within {BROWSER_LAUNCH_TIMEOUT}s on port {debug_port}"
                )

            # 7. 标记就绪，获取 WS URL
            instance.status = "ready"
            instance.last_health_check = time.time()

            async with httpx.AsyncClient() as client:
                try:
                    resp = await client.get(
                        f"http://localhost:{debug_port}/json/version",
                        timeout=5,
                    )
                    if resp.status_code == 200:
                        instance.ws_url = resp.json().get("webSocketDebuggerUrl", "")
                except Exception:
                    instance.ws_url = f"ws://localhost:{debug_port}/devtools/browser"

            logger.info(
                f"[BrowserPool] Instance created: {instance_id[:8]}... "
                f"port={debug_port}, platform={platform or 'generic'}, "
                f"headless={headless}, pid={instance.pid}"
            )

            return instance

    async def destroy_instance(self, instance_id: str, force: bool = False) -> bool:
        """
        销毁浏览器实例

        Args:
            instance_id: 实例 ID
            force: 是否强制 kill

        Returns:
            bool: 是否成功销毁
        """
        async with self._write_lock:
            instance = self.instances.get(instance_id)
            if not instance:
                logger.warning(f"[BrowserPool] Instance {instance_id} not found")
                return False

            if instance.status == "stopped":
                logger.info(f"[BrowserPool] Instance {instance_id} already stopped")
                return True

            logger.info(
                f"[BrowserPool] Destroying instance: {instance_id[:8]}... "
                f"port={instance.debug_port}, pid={instance.pid}"
            )

            # 先标记为 stopped，防止健康检查期间被重新操作
            instance.status = "stopped"

            process = instance.process
            if process is None:
                return True

            # 进程已退出
            if process.poll() is not None:
                logger.info(f"[BrowserPool] Process {instance.pid} already exited (rc={process.returncode})")
                instance.process = None
                instance.pid = None
                return True

            # 优雅关闭
            try:
                if self.system == "Windows":
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        logger.warning(f"[BrowserPool] Force killing process {process.pid}")
                        subprocess.run(
                            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                            capture_output=True,
                            check=False,
                        )
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            logger.error(f"[BrowserPool] Failed to kill process {process.pid}")
                else:
                    if force:
                        import signal
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    else:
                        import signal
                        pgid = os.getpgid(process.pid)
                        os.killpg(pgid, signal.SIGTERM)
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            logger.warning(f"[BrowserPool] Force killing process group {pgid}")
                            os.killpg(pgid, signal.SIGKILL)
                            process.wait(timeout=5)
            except Exception as e:
                logger.error(f"[BrowserPool] Error stopping process: {e}")
                # 尝试最后一次强制杀
                try:
                    if process.poll() is None:
                        process.kill()
                except Exception:
                    pass

            instance.process = None
            instance.pid = None
            instance.ws_url = ""

            logger.info(f"[BrowserPool] Instance {instance_id[:8]}... destroyed, port {instance.debug_port} released")
            return True

    async def get_instance(self, instance_id: str) -> Optional[BrowserInstance]:
        """获取实例详情"""
        return self.instances.get(instance_id)

    async def list_instances(self, status_filter: Optional[str] = None) -> List[BrowserInstance]:
        """
        列出所有实例，可按状态过滤

        Args:
            status_filter: 可选的状态过滤器
        """
        if status_filter:
            return [inst for inst in self.instances.values() if inst.status == status_filter]
        return list(self.instances.values())

    async def get_instance_count(self, status_filter: Optional[str] = None) -> int:
        """获取实例数量"""
        instances = await self.list_instances(status_filter)
        return len(instances)

    async def health_check_instance(self, instance_id: str) -> Dict[str, Any]:
        """
        对指定实例执行健康检查

        Returns:
            dict with status info
        """
        instance = self.instances.get(instance_id)
        if not instance:
            return {"status": "not_found"}

        result = {
            "instance_id": instance_id,
            "debug_port": instance.debug_port,
            "pid": instance.pid,
            "created_at": instance.created_at,
            "uptime": time.time() - instance.created_at if instance.created_at else 0,
            "status": "unknown",
        }

        # 检查进程是否存活
        process_alive = False
        if instance.process:
            process_alive = instance.process.poll() is None

        if not process_alive and instance.pid is not None:
            instance.health_fail_count += 1
            result["status"] = "unhealthy"
            result["detail"] = "Process not running"
        else:
            # Socket 连接检查
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(2)
                    res = s.connect_ex(("localhost", instance.debug_port))
                    if res == 0:
                        # CDP HTTP 检查
                        async with httpx.AsyncClient() as client:
                            try:
                                resp = await client.get(
                                    f"http://localhost:{instance.debug_port}/json/version",
                                    timeout=5,
                                )
                                if resp.status_code == 200:
                                    result["status"] = "ok"
                                    instance.health_fail_count = 0
                                    instance.last_health_check = time.time()
                                    return result
                            except Exception:
                                pass

                        instance.health_fail_count += 1
                        result["status"] = "unhealthy"
                        result["detail"] = "CDP HTTP not responding"
                    else:
                        instance.health_fail_count += 1
                        result["status"] = "unhealthy"
                        result["detail"] = "Socket connection refused"
            except Exception as e:
                instance.health_fail_count += 1
                result["status"] = "unhealthy"
                result["detail"] = str(e)

        # 更新最后检查时间
        instance.last_health_check = time.time()

        # 连续 3 次失败 → 标记为 unhealthy
        if instance.health_fail_count >= 3 and instance.status != "unhealthy":
            instance.status = "unhealthy"
            logger.warning(
                f"[BrowserPool] Instance {instance_id[:8]}... marked as unhealthy "
                f"after {instance.health_fail_count} consecutive failures"
            )

        return result

    async def restart_instance(self, instance_id: str) -> BrowserInstance:
        """
        重启浏览器实例（保持相同端口和 user_data_dir 以恢复登录态）

        Args:
            instance_id: 实例 ID

        Returns:
            BrowserInstance: 重启后的实例
        """
        instance = self.instances.get(instance_id)
        if not instance:
            raise ValueError(f"Instance {instance_id} not found")

        logger.info(
            f"[BrowserPool] Restarting instance: {instance_id[:8]}... "
            f"port={instance.debug_port}, platform={instance.platform_name}"
        )

        # 1. 销毁旧进程
        await self.destroy_instance(instance_id, force=True)

        # 2. 等待端口释放
        await asyncio.sleep(1)

        # 3. 重新启动（使用相同的端口和 user_data_dir）
        async with self._write_lock:
            instance.status = "starting"
            instance.created_at = time.time()
            instance.health_fail_count = 0
            instance.context_count = 0

            instance.process = self.launch_browser(
                browser_path=instance.browser_path,
                debug_port=instance.debug_port,
                headless=instance.headless,
                user_data_dir=instance.user_data_dir,
            )
            instance.pid = instance.process.pid

            ready = await self.wait_for_browser_ready(instance.debug_port)
            if not ready:
                instance.status = "unhealthy"
                raise RuntimeError(
                    f"Browser instance {instance_id} failed to restart on port {instance.debug_port}"
                )

            instance.status = "ready"
            instance.last_health_check = time.time()

            # 获取 WS URL
            async with httpx.AsyncClient() as client:
                try:
                    resp = await client.get(
                        f"http://localhost:{instance.debug_port}/json/version",
                        timeout=5,
                    )
                    if resp.status_code == 200:
                        instance.ws_url = resp.json().get("webSocketDebuggerUrl", "")
                except Exception:
                    instance.ws_url = f"ws://localhost:{instance.debug_port}/devtools/browser"

            logger.info(
                f"[BrowserPool] Instance {instance_id[:8]}... restarted successfully, "
                f"pid={instance.pid}, user_data_dir preserved"
            )

            return instance

    async def cleanup_stale_instances(self, max_age_seconds: int = 300):
        """
        清理已停止超过 max_age_seconds 的实例元数据
        """
        now = time.time()
        to_remove = []

        async with self._write_lock:
            for inst_id, inst in self.instances.items():
                if inst.status == "stopped":
                    if inst.last_health_check > 0:
                        age = now - inst.last_health_check
                    else:
                        age = now - inst.created_at

                    if age > max_age_seconds:
                        to_remove.append(inst_id)

            for inst_id in to_remove:
                del self.instances[inst_id]
                logger.info(f"[BrowserPool] Cleaned up stale instance: {inst_id[:8]}...")

            if to_remove:
                logger.info(f"[BrowserPool] Cleaned up {len(to_remove)} stale instances")

    async def get_metrics(self) -> Dict[str, Any]:
        """获取运行时指标"""
        total = len(self.instances)
        ready_count = sum(1 for i in self.instances.values() if i.status == "ready")
        unhealthy_count = sum(1 for i in self.instances.values() if i.status == "unhealthy")
        starting_count = sum(1 for i in self.instances.values() if i.status == "starting")
        stopped_count = sum(1 for i in self.instances.values() if i.status == "stopped")

        return {
            "total_instances": total,
            "ready": ready_count,
            "unhealthy": unhealthy_count,
            "starting": starting_count,
            "stopped": stopped_count,
            "port_range": f"{CDP_PORT_START}-{CDP_PORT_END}",
            "pool_size": POOL_SIZE,
            "system": self.system,
        }

    async def shutdown_all(self):
        """关闭所有实例（服务关闭时调用）"""
        logger.info("[BrowserPool] Shutting down all instances...")

        instance_ids = list(self.instances.keys())
        for inst_id in instance_ids:
            try:
                await self.destroy_instance(inst_id, force=True)
            except Exception as e:
                logger.error(f"[BrowserPool] Error shutting down {inst_id}: {e}")

        logger.info("[BrowserPool] All instances shut down")
