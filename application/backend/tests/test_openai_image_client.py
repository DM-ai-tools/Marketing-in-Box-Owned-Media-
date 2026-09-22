"""Tests for the OpenAI image-generation gateway. Nothing here touches the live API."""

from __future__ import annotations

import base64
import types

import httpx
import pytest

from app.services import openai_image_client


def test_is_configured_follows_the_env_var(monkeypatch):
    monkeypatch.delenv(openai_image_client.API_KEY_ENV, raising=False)
    assert openai_image_client.is_configured() is False
    monkeypatch.setenv(openai_image_client.API_KEY_ENV, "sk-test")
    assert openai_image_client.is_configured() is True


def test_client_refuses_to_build_without_a_key(monkeypatch):
    monkeypatch.delenv(openai_image_client.API_KEY_ENV, raising=False)
    openai_image_client.reset_client()
    with pytest.raises(openai_image_client.OpenAIImageNotConfigured):
        openai_image_client._client()
    openai_image_client.reset_client()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kwargs,bad_value",
    [
        ({"size": "800x600"}, "800x600"),
        ({"quality": "ultra"}, "ultra"),
        ({"output_format": "gif"}, "gif"),
    ],
)
async def test_invalid_parameters_are_rejected_before_any_request_goes_out(monkeypatch, kwargs, bad_value):
    monkeypatch.delenv(openai_image_client.API_KEY_ENV, raising=False)

    with pytest.raises(openai_image_client.OpenAIImageInvalidRequest, match=bad_value):
        await openai_image_client.generate_image("a hero image", **kwargs)


class _Response:
    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://api.openai.com/v1/images/generations")
            response = httpx.Response(self.status_code, request=request, json=self._payload)
            raise httpx.HTTPStatusError("error", request=request, response=response)

    def json(self):
        return self._payload


@pytest.mark.asyncio
async def test_generate_image_decodes_the_returned_base64(monkeypatch):
    raw = b"not-really-a-png"
    encoded = base64.b64encode(raw).decode("ascii")

    async def post(path, json):
        assert path == "/images/generations"
        assert json["size"] == "1536x1024"
        assert "response_format" not in json  # DALL-E-only param; must not be sent for GPT models
        return _Response({"data": [{"b64_json": encoded}], "output_format": "png"})

    fake = types.SimpleNamespace(post=post)
    monkeypatch.setattr(openai_image_client, "_client", lambda: fake)

    result = await openai_image_client.generate_image("a hero image", size="1536x1024")

    assert result.data == raw
    assert result.output_format == "png"


@pytest.mark.asyncio
async def test_a_response_with_no_image_data_is_an_error(monkeypatch):
    async def post(path, json):
        return _Response({"data": []})

    fake = types.SimpleNamespace(post=post)
    monkeypatch.setattr(openai_image_client, "_client", lambda: fake)

    with pytest.raises(openai_image_client.OpenAIImageError, match="no image data"):
        await openai_image_client.generate_image("a hero image")


@pytest.mark.asyncio
async def test_an_http_error_surfaces_openais_own_message(monkeypatch):
    async def post(path, json):
        return _Response({"error": {"message": "content_policy_violation"}}, status_code=400)

    fake = types.SimpleNamespace(post=post)
    monkeypatch.setattr(openai_image_client, "_client", lambda: fake)

    with pytest.raises(openai_image_client.OpenAIImageError, match="content_policy_violation"):
        await openai_image_client.generate_image("a hero image")
