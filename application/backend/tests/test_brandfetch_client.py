"""Tests for the Brandfetch gateway. Nothing here touches the live API."""

from __future__ import annotations

import types

import httpx
import pytest

from app.services import brandfetch_client


def test_is_configured_follows_the_env_var(monkeypatch):
    monkeypatch.delenv(brandfetch_client.API_KEY_ENV, raising=False)
    assert brandfetch_client.is_configured() is False
    monkeypatch.setenv(brandfetch_client.API_KEY_ENV, "bf-test")
    assert brandfetch_client.is_configured() is True


def test_client_refuses_to_build_without_a_key(monkeypatch):
    monkeypatch.delenv(brandfetch_client.API_KEY_ENV, raising=False)
    brandfetch_client.reset_client()
    with pytest.raises(brandfetch_client.BrandfetchNotConfigured):
        brandfetch_client._client()
    brandfetch_client.reset_client()


def test_colors_are_ranked_brand_identity_first():
    ranked = brandfetch_client._rank_colors(
        [
            {"hex": "#111111", "type": "light"},
            {"hex": "#222222", "type": "brand"},
            {"hex": "#333333", "type": "accent"},
        ]
    )
    assert ranked == ("#222222", "#333333", "#111111")


def test_logo_prefers_a_wordmark_over_an_icon_and_svg_over_raster():
    url = brandfetch_client._best_logo_url(
        [
            {"type": "icon", "theme": "light", "formats": [{"src": "https://x/icon.png", "format": "png"}]},
            {
                "type": "logo",
                "theme": "light",
                "formats": [
                    {"src": "https://x/logo.png", "format": "png"},
                    {"src": "https://x/logo.svg", "format": "svg"},
                ],
            },
        ]
    )
    assert url == "https://x/logo.svg"


def test_fonts_are_split_by_title_vs_body():
    fonts = [{"name": "Poppins", "type": "title"}, {"name": "Inter", "type": "body"}]
    assert brandfetch_client._font_by_type(fonts, "title") == "Poppins"
    assert brandfetch_client._font_by_type(fonts, "body") == "Inter"


class _Response:
    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://api.brandfetch.io/v2/brands/domain/client.com")
            response = httpx.Response(self.status_code, request=request, json=self._payload)
            raise httpx.HTTPStatusError("error", request=request, response=response)

    def json(self):
        return self._payload


@pytest.mark.asyncio
async def test_retrieve_brand_parses_the_full_record(monkeypatch):
    async def get(path):
        assert path == "/v2/brands/domain/client.com"
        return _Response(
            {
                "colors": [{"hex": "#a4d36b", "type": "brand"}],
                "logos": [{"type": "logo", "theme": "light", "formats": [{"src": "https://client.com/logo.svg", "format": "svg"}]}],
                "fonts": [{"name": "Montserrat", "type": "title"}, {"name": "Inter", "type": "body"}],
            }
        )

    fake = types.SimpleNamespace(get=get)
    monkeypatch.setattr(brandfetch_client, "_client", lambda: fake)

    record = await brandfetch_client.retrieve_brand("client.com")

    assert record.colors == ("#a4d36b",)
    assert record.logo_url == "https://client.com/logo.svg"
    assert record.heading_font == "Montserrat"
    assert record.body_font == "Inter"
    assert record.available


@pytest.mark.asyncio
async def test_retrieve_brand_translates_an_http_error(monkeypatch):
    async def get(path):
        return _Response({"message": "domain not found"}, status_code=404)

    fake = types.SimpleNamespace(get=get)
    monkeypatch.setattr(brandfetch_client, "_client", lambda: fake)

    with pytest.raises(brandfetch_client.BrandfetchError, match="domain not found"):
        await brandfetch_client.retrieve_brand("nope.example")
