# -*- coding: utf-8 -*-
"""
签名微服务 - FastAPI 入口

独立部署的签名服务，解耦签名逻辑。
端口: 8082
"""

from contextlib import asynccontextmanager
from typing import Dict, Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

from signers.base import SignRequest, SignResult
from signers.xhs_signer import XhsSigner
from signers.dy_signer import DySigner

load_dotenv()

# 平台签名器注册表
_signer_cache: Dict[str, "AbstractSigner"] = {}


def get_signer(platform: str):
    """获取平台签名器 (懒加载 + 缓存)"""
    if platform in _signer_cache:
        return _signer_cache[platform]

    if platform == "xhs":
        import os
        signer = XhsSigner(
            a1=os.getenv("XHS_A1", ""),
            web_session=os.getenv("XHS_WEB_SESSION", ""),
        )
    elif platform in ("dy", "douyin"):
        import os
        signer = DySigner(
            ms_token=os.getenv("DY_MS_TOKEN", ""),
            ttwid=os.getenv("DY_TTWID", ""),
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")

    _signer_cache[platform] = signer
    return signer


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    _signer_cache.clear()


app = FastAPI(
    title="MediaCrawler Signer Service",
    description="Independent signature service for MediaCrawler Pro",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    return {
        "service": "MediaCrawler Signer Service",
        "version": "1.0.0",
        "supported_platforms": list(_signer_cache.keys()) or ["xhs", "dy"],
    }


@app.post("/api/sign", response_model=SignResult)
async def sign_request(request: SignRequest) -> SignResult:
    """对请求进行签名"""
    signer = get_signer(request.platform)
    result = await signer.sign(request)
    return result


@app.post("/api/sign/batch")
async def sign_batch(requests: list[SignRequest]) -> list[SignResult]:
    """批量签名"""
    results = []
    for req in requests:
        signer = get_signer(req.platform)
        result = await signer.sign(req)
        results.append(result)
    return results


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "platforms": ["xhs", "dy", "ks", "bili"]}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8082)
