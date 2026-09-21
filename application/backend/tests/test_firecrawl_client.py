"""Tests for the Firecrawl gateway.

Nothing here touches the live API. The seam is the cached client: a fake stands in for the
`httpx.AsyncClient` and `_poll`'s sleep is patched out so the test suite does not actually wait.
"""

from __future__ import annotations

import types

import httpx
import pytest

from app.services import firecrawl_client


def test_is_configured_follows_the_env_var(monkeypatch):
    monkeypatch.delenv(firecrawl_client.API_KEY_ENV, raising=False)
    assert firecrawl_client.is_configured() is False
    monkeypatch.setenv(firecrawl_client.API_KEY_ENV, "fc-test")
    assert firecrawl_client.is_configured() is True


def test_client_refuses_to_build_without_a_key(monkeypatch):
    monkeypatch.delenv(firecrawl_client.API_KEY_ENV, raising=False)
    firecrawl_client.reset_client()
    with pytest.raises(firecrawl_client.FirecrawlNotConfigured):
        firecrawl_client._client()
    firecrawl_client.reset_client()


class _Response:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://api.firecrawl.dev/v2/extract")
            response = httpx.Response(self.status_code, request=request, json=self._payload)
            raise httpx.HTTPStatusError("error", request=request, response=response)

    def json(self):
        return self._payload


@pytest.mark.asyncio
async def test_extract_brand_tokens_polls_until_complete(monkeypatch):
    calls = {"polls": 0}

    async def post(path, json):
        assert path == "/extract"
        assert json["urls"] == ["https://client.com/"]
        return _Response({"success": True, "id": "job-1"})

    async def get(path):
        calls["polls"] += 1
        if calls["polls"] < 2:
            return _Response({"status": "processing"})
        return _Response(
            {
                "status": "completed",
                "data": {"primaryColor": "#123456", "logoUrl": "https://client.com/logo.png"},
                "tokensUsed": 42,
            }
        )

    fake = types.SimpleNamespace(post=post, get=get)
    monkeypatch.setattr(firecrawl_client, "_client", lambda: fake)
    monkeypatch.setattr(firecrawl_client, "_POLL_INTERVAL_SECONDS", 0)

    tokens = await firecrawl_client.extract_brand_tokens("https://client.com/")

    assert tokens.primary_color == "#123456"
    assert tokens.logo_url == "https://client.com/logo.png"
    assert tokens.available
    assert calls["polls"] == 2


@pytest.mark.asyncio
async def test_extract_brand_tokens_raises_on_a_failed_job(monkeypatch):
    async def post(path, json):
        return _Response({"success": True, "id": "job-2"})

    async def get(path):
        return _Response({"status": "failed"})

    fake = types.SimpleNamespace(post=post, get=get)
    monkeypatch.setattr(firecrawl_client, "_client", lambda: fake)

    with pytest.raises(firecrawl_client.FirecrawlError):
        await firecrawl_client.extract_brand_tokens("https://client.com/")


@pytest.mark.asyncio
async def test_extract_brand_tokens_raises_when_no_job_id_comes_back(monkeypatch):
    async def post(path, json):
        return _Response({"success": True})

    fake = types.SimpleNamespace(post=post, get=None)
    monkeypatch.setattr(firecrawl_client, "_client", lambda: fake)

    with pytest.raises(firecrawl_client.FirecrawlError):
        await firecrawl_client.extract_brand_tokens("https://client.com/")
