"""The one place this backend talks to Firecrawl.

Why this exists
----------------
Context.dev is, and stays, the primary source for `DESIGN.md` (see `app/services/design_md.py`
and the "One API and one key for web data" rule in `CLAUDE.md`). This module exists for a narrow,
secondary job: when Context.dev's `/web/styleguide` and `/web/fonts` and the free local CSS parse
in `design_tokens.py` *all* leave a field unfilled — a bot-walled page, a JS-heavy theme the local
parse cannot resolve — Firecrawl's structured extraction is tried before giving up on that field.

It is never called unless `design_md._brand_gaps` finds something missing, and it never overrides
a value Context.dev or the local parse already found. See `design_md._capture_brand_fallback`.

What this module returns
-------------------------
`extract_brand_tokens` asks Firecrawl's `/extract` for a fixed JSON Schema (colors, fonts, logo,
button radius) rather than scraping HTML and re-parsing it here — that would just be a second,
worse copy of `design_tokens.py`. The values come back as raw strings; validation (is this really
a hex colour?) happens in `design_md.py`'s merge, the same place that already validates
Context.dev's own colours, so there is exactly one place a bad value gets caught.

`/extract` is asynchronous: POST returns a job id, and the result is polled from
`GET /extract/{id}`. `_poll` bounds that with `_MAX_POLL_SECONDS` rather than waiting forever on a
job that never finishes.

Testing
-------
Tests must not reach the live API. Patch the functions in this module — never `_client()`.

Docs
----
* Extract   https://docs.firecrawl.dev/api-reference/endpoint/extract
* Poll      https://docs.firecrawl.dev/api-reference/endpoint/extract-get
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import httpx

logger = logging.getLogger(__name__)

API_KEY_ENV = "FIRECRAWL_API_KEY"
_BASE_URL = "https://api.firecrawl.dev/v2"

_TIMEOUT_SECONDS = 30.0
# Bounds the poll loop in `extract_brand_tokens`. A brand-token extraction is a handful of fields
# off one page, not a crawl — if it has not finished in this long it is not going to.
_MAX_POLL_SECONDS = 45.0
_POLL_INTERVAL_SECONDS = 2.0

_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "primaryColor": {"type": "string", "description": "The site's main brand hex color, e.g. #1a73e8"},
        "secondaryColor": {"type": "string", "description": "A secondary brand hex color, if distinct from the primary"},
        "backgroundColor": {"type": "string", "description": "The page's main background hex color"},
        "textColor": {"type": "string", "description": "The body text hex color"},
        "headingFont": {"type": "string", "description": "The font family used for headings"},
        "bodyFont": {"type": "string", "description": "The font family used for body text"},
        "logoUrl": {"type": "string", "description": "Absolute URL of the site's primary logo image"},
        "buttonBorderRadius": {"type": "string", "description": "CSS border-radius of the primary button, e.g. 8px"},
    },
}


class FirecrawlError(Exception):
    """A Firecrawl call did not produce a usable answer."""


class FirecrawlNotConfigured(FirecrawlError):
    """`FIRECRAWL_API_KEY` is not set. Callers treat this as "skip me", not a failure."""


def is_configured() -> bool:
    return bool(os.environ.get(API_KEY_ENV, "").strip())


@lru_cache(maxsize=1)
def _client() -> httpx.AsyncClient:
    """The shared async client. Cached so the connection pool is reused across requests."""
    key = os.environ.get(API_KEY_ENV, "").strip()
    if not key:
        raise FirecrawlNotConfigured(
            f"{API_KEY_ENV} is not set, so Firecrawl is unavailable. Add it to the backend .env."
        )
    return httpx.AsyncClient(
        base_url=_BASE_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        timeout=_TIMEOUT_SECONDS,
    )


def reset_client() -> None:
    """Drop the cached client. For tests and for a key rotated without a restart."""
    _client.cache_clear()


def _fail(what: str, exc: Exception) -> FirecrawlError:
    if isinstance(exc, httpx.TimeoutException):
        detail = f"Firecrawl did not answer within {int(_TIMEOUT_SECONDS)}s."
    elif isinstance(exc, httpx.ConnectError):
        detail = "Could not reach Firecrawl from this server."
    elif isinstance(exc, httpx.HTTPStatusError):
        detail = f"Firecrawl answered HTTP {exc.response.status_code}: {_status_body(exc)}"
    else:
        detail = str(exc) or exc.__class__.__name__
    return FirecrawlError(f"{what}: {detail}")


def _status_body(exc: httpx.HTTPStatusError) -> str:
    try:
        body = exc.response.json()
    except ValueError:
        return exc.response.text[:300]
    if isinstance(body, dict):
        message = body.get("error") or body.get("message")
        if message:
            return str(message)[:300]
    return str(body)[:300]


@dataclass(frozen=True)
class BrandTokens:
    """The handful of brand fields this app asks Firecrawl for. Raw strings — `design_md.py`
    validates and merges them, the same place Context.dev's own values are validated."""

    source_url: str
    primary_color: str | None = None
    secondary_color: str | None = None
    background_color: str | None = None
    text_color: str | None = None
    heading_font: str | None = None
    body_font: str | None = None
    logo_url: str | None = None
    button_border_radius: str | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def available(self) -> bool:
        return any(
            (
                self.primary_color,
                self.secondary_color,
                self.background_color,
                self.text_color,
                self.heading_font,
                self.body_font,
                self.logo_url,
            )
        )


async def extract_brand_tokens(url: str) -> BrandTokens:
    """Ask Firecrawl's structured extraction for this page's brand basics.

    Only ever called as a fallback — see the module docstring. Raises `FirecrawlError` on failure
    or timeout; callers treat that as "this source had nothing" and carry on with what they have.
    """
    logger.info("Firecrawl API executing operation=extract_brand_tokens url=%r", url)
    client = _client()
    try:
        submit = await client.post("/extract", json={"urls": [url], "schema": _SCHEMA})
        submit.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("Firecrawl API error operation=extract_brand_tokens url=%r error=%s", url, exc)
        raise _fail(f"Could not submit a Firecrawl extract for {url}", exc) from exc

    payload = submit.json()
    job_id = payload.get("id")
    if not job_id:
        raise FirecrawlError(f"Firecrawl did not return a job id for {url}.")

    try:
        data = await _poll(client, job_id, url)
    except FirecrawlError as exc:
        logger.error("Firecrawl API error operation=extract_brand_tokens url=%r error=%s", url, exc)
        raise

    return BrandTokens(
        source_url=url,
        primary_color=data.get("primaryColor") or None,
        secondary_color=data.get("secondaryColor") or None,
        background_color=data.get("backgroundColor") or None,
        text_color=data.get("textColor") or None,
        heading_font=data.get("headingFont") or None,
        body_font=data.get("bodyFont") or None,
        logo_url=data.get("logoUrl") or None,
        button_border_radius=data.get("buttonBorderRadius") or None,
        raw=data,
    )


async def _poll(client: httpx.AsyncClient, job_id: str, url: str) -> dict[str, Any]:
    elapsed = 0.0
    while elapsed <= _MAX_POLL_SECONDS:
        try:
            response = await client.get(f"/extract/{job_id}")
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise _fail(f"Could not poll the Firecrawl extract job for {url}", exc) from exc

        payload = response.json()
        status = payload.get("status")
        if status == "completed":
            logger.info("Firecrawl extract completed url=%r tokens_used=%s", url, payload.get("tokensUsed"))
            return payload.get("data") or {}
        if status in ("failed", "cancelled"):
            raise FirecrawlError(f"Firecrawl extract for {url} {status}.")

        await asyncio.sleep(_POLL_INTERVAL_SECONDS)
        elapsed += _POLL_INTERVAL_SECONDS

    raise FirecrawlError(f"Firecrawl extract for {url} did not finish within {int(_MAX_POLL_SECONDS)}s.")
