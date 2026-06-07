# -*- coding: utf-8 -*-
import pytest
import httpx
from signer import SignerClient


@pytest.mark.asyncio
async def test_signer_fail_fast_raises(monkeypatch):
    import signer as signer_mod
    monkeypatch.setattr(signer_mod, "SIGNER_FAIL_FAST", True)
    client = SignerClient(base_url="http://127.0.0.1:59999")

    async def _boom(self, url, **kwargs):
        raise httpx.ConnectError("down", request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", _boom)
    with pytest.raises(RuntimeError):
        await client.sign("xhs")
