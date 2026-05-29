# -*- coding: utf-8 -*-
"""
Crawler Service API Server
Start command: uvicorn api.main:app --port 8081 --reload
Or: python -m api.main
"""
import asyncio
import subprocess
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI

from .routers import crawler_router, websocket_router, crawler_pro_router, comment_crawler_router

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # 关闭时：优雅停止调度器中的所有运行中任务
    try:
        from engine.task_scheduler import scheduler
        await scheduler.shutdown(timeout=10.0)
    except Exception:
        pass


app = FastAPI(
    title="MediaCrawler Crawler Service",
    description="Crawler control and real-time log streaming via WebSocket",
    version="2.1.0",
    lifespan=lifespan,
)

app.include_router(crawler_router, prefix="/api")
app.include_router(crawler_pro_router, prefix="/api")
app.include_router(comment_crawler_router, prefix="/api")
app.include_router(websocket_router, prefix="/api")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "Crawler-Service"}


@app.get("/api/env/check")
async def check_environment():
    try:
        process = await asyncio.create_subprocess_exec(
            "uv", "run", "main.py", "--help",
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd="."
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30.0)
        if process.returncode == 0:
            return {"success": True, "message": "MediaCrawler environment configured correctly",
                    "output": stdout.decode("utf-8", errors="ignore")[:500]}
        error_msg = stderr.decode("utf-8", errors="ignore") or stdout.decode("utf-8", errors="ignore")
        return {"success": False, "message": "Environment check failed", "error": error_msg[:500]}
    except asyncio.TimeoutError:
        return {"success": False, "message": "Environment check timeout",
                "error": "Command execution exceeded 30 seconds"}
    except FileNotFoundError:
        return {"success": False, "message": "uv command not found",
                "error": "Please ensure uv is installed and configured in system PATH"}
    except Exception as e:
        return {"success": False, "message": "Environment check error", "error": str(e)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8081)
