# Browser-Service Dockerfile
# 独立浏览器池服务, 通过 REST API 管理 Chrome 实例生命周期
# 基于 Python 3.11 + Google Chrome (CDP 协议)
# 对外暴露 CDP WebSocket 端口, Crawler-Service 通过 connect_over_cdp 直连
# 端口 9500

FROM python:3.11-slim

WORKDIR /app

# 安装 uv
RUN pip install --no-cache-dir uv

# 安装系统依赖: Chrome 运行库 + Playwright 依赖 + Xvfb(虚拟显示)
# 注: 不安装 Playwright 自带的 Chromium, 使用 Google Chrome Stable
RUN apt-get update && apt-get install -y --no-install-recommends \
    # C 编译器 (uv sync 时某些包需要从源码编译)
    build-essential \
    # Chrome/Playwright 运行时依赖
    libasound2 libatk-bridge2.0-0 libatk1.0-0 libcups2 libdbus-1-3 \
    libdrm2 libgbm1 libgtk-3-0 libnspr4 libnss3 libu2f-udev \
    libxcomposite1 libxdamage1 libxfixes3 libxkbcommon0 libxrandr2 \
    xdg-utils \
    # opencv-python 运行时依赖 (保持与 Crawler-Service 一致)
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
    # Chrome 安装工具
    wget gnupg ca-certificates \
    # 中文字体 (浏览器渲染中文页面)
    fonts-wqy-zenhei fonts-wqy-microhei \
    # 虚拟显示器 (Chrome 需要 X 服务器, 用 Xvfb 替代)
    xvfb \
    # 进程管理工具
    procps \
    && rm -rf /var/lib/apt/lists/*

# 安装 Google Chrome Stable (CDP 模式需要真实 Chrome)
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | \
    gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] \
    http://dl.google.com/linux/chrome/deb/ stable main" \
    > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y --no-install-recommends \
    google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# 验证 Chrome 安装
RUN google-chrome --version

# 利用 Docker 层缓存: 先复制依赖文件
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen || uv sync

# 复制源代码
COPY . .

# PYTHONPATH 确保模块导入正确
ENV PYTHONPATH=.

# 虚拟显示器
ENV DISPLAY=:99

# 服务端口 (REST API)
EXPOSE 9500

# CDP 调试端口范围 (每个 Chrome 实例占用一个端口)
# Docker Compose 中映射: "9222-9229:9222-9229"
EXPOSE 9222-9229

# 启动: Xvfb 虚拟显示器 + uvicorn FastAPI 服务
CMD ["sh", "-c", "Xvfb :99 -screen 0 1920x1080x24 -ac +extension RANDR & uv run uvicorn api.main:app --host 0.0.0.0 --port 9500"]
