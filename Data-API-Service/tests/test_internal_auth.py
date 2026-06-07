# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
os.environ["INTERNAL_API_TOKEN"] = "test-internal-token"

from fastapi.testclient import TestClient
from api.routers.internal import _INTERNAL_API_TOKEN, router
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_internal_requires_token():
    assert client.get("/api/internal/tasks").status_code == 403


def test_internal_accepts_token():
    resp = client.get("/api/internal/tasks", headers={"X-API-Token": _INTERNAL_API_TOKEN})
    assert resp.status_code in (200, 500)
