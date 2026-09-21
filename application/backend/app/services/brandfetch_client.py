"""The one place this backend talks to Brandfetch.

Why this exists
----------------
Same role as `firecrawl_client.py`, one tier further down: Brandfetch is a dedicated brand-data
index (colours, logos, fonts by domain), tried only when Context.dev, the local CSS parse, *and*
Firecrawl have all left a field unfilled. It never runs unless `design_md._brand_gaps` says
something is still missing, and it never overrides a value found upstream. See
`design_md._capture_brand_fallback`.

Kept deliberately dumb, like `context_dev.BrandRecord`: this module returns the API's own colours
ranked in its own priority order and the raw logo URL, and leaves picking "primary" vs
"secondary" to `design_md.py`'s merge — the one place that logic already exists for Context.dev's
`accent`/`background`/`text` triple, so there is one mapping to reason about, not two.

Testing
-------
Tests must not reach the live API. Patch the functions in this module — never `_client()`.

Docs
----
* Brand API   https://docs.brandfetch.com/reference/brand-api
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import httpx

logger = logging.getLogger(__name__)

API_KEY_ENV = "BRANDFETCH_API_KEY"
_BASE_URL = "https://api.brandfetch.io"
_TIMEOUT_SECONDS = 20.0

# Brandfetch's own colour-type ranking, brand identity first. Used to pick which hex is "primary"
# vs "secondary" further down, before any per-project renaming happens in design_md.py.
_COLOR_TYPE_ORDER = ("brand", "accent", "dark", "light")

# Logo type preference (a wordmark over a bare icon) and format preference (a vector over a
# raster) when more than one is offered for the same theme.
_LOGO_TYPE_ORDER = ("logo", "symbol", "icon", "other")
_LOGO_FORMAT_ORDER = ("svg", "png", "webp", "jpeg")


class BrandfetchError(Exception):
    """A Brandfetch call did not produce a usable answer."""


class BrandfetchNotConfigured(BrandfetchError):
    """`BRANDFETCH_API_KEY` is not set. Callers treat this as "skip me", not a failure."""


def is_configured() -> bool:
    return bool(os.environ.get(API_KEY_ENV, "").strip())


@lru_cache(maxsize=1)
def _client() -> httpx.AsyncClient:
    key = os.environ.get(API_KEY_ENV, "").strip()
    if not key:
        raise BrandfetchNotConfigured(
            f"{API_KEY_ENV} is not set, so Brandfetch is unavailable. Add it to the backend .env."
        )
    return httpx.AsyncClient(
        base_url=_BASE_URL,
        headers={"Authorization": f"Bearer {key}"},
        timeout=_TIMEOUT_SECONDS,
    )


def reset_client() -> None:
    """Drop the cached client. For tests and for a key rotated without a restart."""
    _client.cache_clear()


def _fail(what: str, exc: Exception) -> BrandfetchError:
    if isinstance(exc, httpx.TimeoutException):
        detail = f"Brandfetch did not answer within {int(_TIMEOUT_SECONDS)}s."
    elif isinstance(exc, httpx.ConnectError):
        detail = "Could not reach Brandfetch from this server."
    elif isinstance(exc, httpx.HTTPStatusError):
        detail = f"Brandfetch answered HTTP {exc.response.status_code}: {_status_body(exc)}"
    else:
        detail = str(exc) or exc.__class__.__name__
    return BrandfetchError(f"{what}: {detail}")


def _status_body(exc: httpx.HTTPStatusError) -> str:
    try:
        body = exc.response.json()
    except ValueError:
        return exc.response.text[:300]
    if isinstance(body, dict):
        message = body.get("message") or body.get("error")
        if message:
            return str(message)[:300]
    return str(body)[:300]


@dataclass(frozen=True)
class BrandRecord:
    """A domain's brand basics, as Brandfetch ranks them."""

    domain: str
    #: Hex strings, ranked brand-identity-first per `_COLOR_TYPE_ORDER`.
    colors: tuple[str, ...] = ()
    logo_url: str | None = None
    heading_font: str | None = None
    body_font: str | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def available(self) -> bool:
        return bool(self.colors or self.logo_url or self.heading_font or self.body_font)


def _rank_colors(raw_colors: list[dict[str, Any]]) -> tuple[str, ...]:
    def sort_key(entry: dict[str, Any]) -> int:
        color_type = entry.get("type")
        return _COLOR_TYPE_ORDER.index(color_type) if color_type in _COLOR_TYPE_ORDER else len(_COLOR_TYPE_ORDER)

    ranked = sorted((c for c in raw_colors if isinstance(c, dict) and c.get("hex")), key=sort_key)
    return tuple(str(c["hex"]) for c in ranked)


def _best_logo_url(raw_logos: list[dict[str, Any]]) -> str | None:
    def logo_key(entry: dict[str, Any]) -> tuple[int, int]:
        logo_type = entry.get("type")
        return (
            _LOGO_TYPE_ORDER.index(logo_type) if logo_type in _LOGO_TYPE_ORDER else len(_LOGO_TYPE_ORDER),
            0 if entry.get("theme") in (None, "light") else 1,
        )

    for logo in sorted((l for l in raw_logos if isinstance(l, dict)), key=logo_key):
        formats = logo.get("formats") or []

        def format_key(fmt: dict[str, Any]) -> int:
            kind = fmt.get("format")
            return _LOGO_FORMAT_ORDER.index(kind) if kind in _LOGO_FORMAT_ORDER else len(_LOGO_FORMAT_ORDER)

        for fmt in sorted((f for f in formats if isinstance(f, dict) and f.get("src")), key=format_key):
            return str(fmt["src"])
    return None


def _font_by_type(raw_fonts: list[dict[str, Any]], font_type: str) -> str | None:
    for entry in raw_fonts:
        if isinstance(entry, dict) and entry.get("type") == font_type and entry.get("name"):
            return str(entry["name"])
    return None


async def retrieve_brand(domain: str) -> BrandRecord:
    """Resolve a bare domain (no scheme) to its brand basics.

    Only ever called as a fallback for a specific missing field — see the module docstring.
    Raises `BrandfetchError` on failure; callers treat that as "this source had nothing".
    """
    logger.info("Brandfetch API executing operation=retrieve_brand domain=%r", domain)
    try:
        response = await _client().get(f"/v2/brands/domain/{domain}")
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("Brandfetch API error operation=retrieve_brand domain=%r error=%s", domain, exc)
        raise _fail(f"Could not retrieve the Brandfetch record for {domain}", exc) from exc

    raw = response.json()
    if not isinstance(raw, dict):
        raise BrandfetchError(f"Brandfetch returned an unexpected shape for {domain}.")

    colors = _rank_colors(raw.get("colors") or [])
    logo_url = _best_logo_url(raw.get("logos") or [])
    fonts = raw.get("fonts") or []
    heading_font = _font_by_type(fonts, "title")
    body_font = _font_by_type(fonts, "body")

    logger.info(
        "Brandfetch retrieve_brand domain=%r colors=%s logo=%s fonts=%s",
        domain,
        len(colors),
        bool(logo_url),
        bool(heading_font or body_font),
    )

    return BrandRecord(
        domain=domain,
        colors=colors,
        logo_url=logo_url,
        heading_font=heading_font,
        body_font=body_font,
        raw=raw,
    )
