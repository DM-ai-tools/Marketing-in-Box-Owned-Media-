"""The one place this backend talks to OpenAI's image generation endpoint.

Replaces Runway. Two real differences from `runway_client.py`, which this module's shape mirrors
everywhere else:

* **Synchronous.** `POST /v1/images/generations` returns the image in the same response — no task
  id, no polling loop.
* **Bytes, not a URL.** Confirmed against OpenAI's own parameter reference before writing this:
  `response_format` (which selects `url` vs `b64_json`) is documented as "DALL-E 2/3 only" — GPT
  image models (`gpt-image-1`, `gpt-image-2`, ...) always return `data[0].b64_json`, never a
  hosted URL. Runway hosted the file for you; OpenAI does not. So this module returns raw bytes,
  and `app/services/media_storage.py` is what turns them into a URL a prompt can reference —
  saving them anywhere else, or embedding them as a data URI, is not this module's job. See that
  module's docstring for why a data URI is the one thing not to do here.

Testing
-------
Tests must not reach the live API. Patch the functions in this module — never `_client()`.

Docs
----
* Image generation guide   https://platform.openai.com/docs/guides/image-generation
* API reference            https://platform.openai.com/docs/api-reference/images/create
"""

from __future__ import annotations

import base64
import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import httpx

logger = logging.getLogger(__name__)

API_KEY_ENV = "OPENAI_API_KEY"
MODEL_ENV = "OPENAI_IMAGE_MODEL"
BASE_URL = "https://api.openai.com/v1"
_TIMEOUT_SECONDS = 120.0

DEFAULT_MODEL = "gpt-image-2"

# The named sizes GPT image models accept, confirmed from OpenAI's own parameter table. A custom
# WIDTHxHEIGHT is also legal there (multiples of 16, 1:3-3:1 aspect, max 3840 either edge), but
# nothing in this pipeline needs a size finer-grained than these three, so only they are offered —
# an unbounded custom-size surface is more to validate for no benefit yet.
VALID_SIZES = frozenset({"auto", "1024x1024", "1536x1024", "1024x1536"})
DEFAULT_SIZE = "1536x1024"

VALID_QUALITIES = frozenset({"low", "medium", "high", "auto"})
DEFAULT_QUALITY = "auto"

VALID_OUTPUT_FORMATS = frozenset({"png", "jpeg", "webp"})
DEFAULT_OUTPUT_FORMAT = "png"


class OpenAIImageError(Exception):
    """An OpenAI image request failed or returned an unusable response."""


class OpenAIImageNotConfigured(OpenAIImageError):
    """`OPENAI_API_KEY` is not set. Callers treat this as "skip me", not a failure."""


class OpenAIImageInvalidRequest(OpenAIImageError):
    """The request was bad before it ever left this backend — an operator-actionable 422, not a
    502 upstream failure. See the size/quality/output_format checks in `generate_image`."""


def is_configured() -> bool:
    return bool(os.environ.get(API_KEY_ENV, "").strip())


@lru_cache(maxsize=1)
def _client() -> httpx.AsyncClient:
    """The shared async client. Cached so the connection pool is reused across requests."""
    key = os.environ.get(API_KEY_ENV, "").strip()
    if not key:
        raise OpenAIImageNotConfigured(
            f"{API_KEY_ENV} is not set, so OpenAI image generation is unavailable. Add it to the "
            "backend .env."
        )
    return httpx.AsyncClient(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        timeout=_TIMEOUT_SECONDS,
    )


@lru_cache(maxsize=1)
def _edit_client() -> httpx.AsyncClient:
    """A second client for `/images/edits`, without `_client()`'s forced `Content-Type: application/json`.

    That endpoint is multipart (it uploads reference image bytes alongside the prompt), and httpx
    has to compute its own boundary header for that — a client-level `application/json` default
    would fight it on every edit request.
    """
    key = os.environ.get(API_KEY_ENV, "").strip()
    if not key:
        raise OpenAIImageNotConfigured(
            f"{API_KEY_ENV} is not set, so OpenAI image generation is unavailable. Add it to the "
            "backend .env."
        )
    return httpx.AsyncClient(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {key}"},
        timeout=_TIMEOUT_SECONDS,
    )


def reset_client() -> None:
    """Drop the cached clients. For tests and for a key rotated without a restart."""
    _client.cache_clear()
    _edit_client.cache_clear()


def _fail(what: str, exc: Exception) -> OpenAIImageError:
    if isinstance(exc, httpx.TimeoutException):
        detail = f"OpenAI did not answer within {int(_TIMEOUT_SECONDS)}s."
    elif isinstance(exc, httpx.ConnectError):
        detail = "Could not reach OpenAI from this server."
    elif isinstance(exc, httpx.HTTPStatusError):
        detail = f"OpenAI answered HTTP {exc.response.status_code}: {_status_body(exc)}"
    else:
        detail = str(exc) or exc.__class__.__name__
    return OpenAIImageError(f"{what}: {detail}")


def _status_body(exc: httpx.HTTPStatusError) -> str:
    try:
        body = exc.response.json()
    except ValueError:
        return exc.response.text[:300]
    if isinstance(body, dict):
        error = body.get("error")
        message = error.get("message") if isinstance(error, dict) else body.get("message")
        if message:
            return str(message)[:300]
    return str(body)[:300]


@dataclass(frozen=True)
class GeneratedImageBytes:
    """One image, straight off the API. `media_storage.save_generated_image` is what gives this
    a URL — nothing in this module writes to disk or knows this app has a media route."""

    data: bytes
    output_format: str


async def generate_image(
    prompt: str,
    *,
    size: str = DEFAULT_SIZE,
    quality: str = DEFAULT_QUALITY,
    output_format: str = DEFAULT_OUTPUT_FORMAT,
    model: str | None = None,
) -> GeneratedImageBytes:
    """Generate one image and return its decoded bytes. Synchronous — no task id, no polling."""
    if size not in VALID_SIZES:
        raise OpenAIImageInvalidRequest(
            f"{size!r} is not a size OpenAI's image models accept. Valid values: "
            f"{', '.join(sorted(VALID_SIZES))}."
        )
    if quality not in VALID_QUALITIES:
        raise OpenAIImageInvalidRequest(
            f"{quality!r} is not a quality OpenAI's image models accept. Valid values: "
            f"{', '.join(sorted(VALID_QUALITIES))}."
        )
    if output_format not in VALID_OUTPUT_FORMATS:
        raise OpenAIImageInvalidRequest(
            f"{output_format!r} is not an output_format OpenAI's image models accept. Valid "
            f"values: {', '.join(sorted(VALID_OUTPUT_FORMATS))}."
        )

    selected_model = model or os.environ.get(MODEL_ENV, DEFAULT_MODEL)
    payload: dict[str, Any] = {
        "model": selected_model,
        "prompt": prompt,
        "size": size,
        "quality": quality,
        "output_format": output_format,
        "n": 1,
    }

    logger.info(
        "OpenAI Image API executing operation=generate model=%s size=%s quality=%s",
        selected_model,
        size,
        quality,
    )
    try:
        response = await _client().post("/images/generations", json=payload)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("OpenAI Image API error operation=generate model=%s error=%s", selected_model, exc)
        raise _fail("Could not generate an image with OpenAI", exc) from exc

    payload_out = response.json()
    entries = payload_out.get("data") or []
    if not entries or not entries[0].get("b64_json"):
        logger.error(
            "OpenAI Image API error operation=generate model=%s error=%s",
            selected_model,
            "response had no b64_json",
        )
        raise OpenAIImageError("OpenAI returned no image data for this prompt.")

    try:
        data = base64.b64decode(entries[0]["b64_json"])
    except (ValueError, TypeError) as exc:
        raise OpenAIImageError(f"OpenAI returned image data that could not be decoded: {exc}") from exc

    returned_format = payload_out.get("output_format") or output_format
    logger.info(
        "OpenAI Image API used operation=generate model=%s bytes=%s format=%s",
        selected_model,
        len(data),
        returned_format,
    )
    return GeneratedImageBytes(data=data, output_format=returned_format)


# How many reference images `edit_image` will download and upload per call. OpenAI's edit endpoint
# accepts several, but each one is a real download plus a few hundred KB of upload — one hero shot
# plus a couple of supporting photos is enough to ground the subject without turning one brief into
# a slow multi-megabyte request.
_MAX_REFERENCE_IMAGES = 3

_CONTENT_TYPE_EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


async def edit_image(
    prompt: str,
    reference_urls: tuple[str, ...],
    *,
    size: str = DEFAULT_SIZE,
    quality: str = DEFAULT_QUALITY,
    model: str | None = None,
) -> GeneratedImageBytes:
    """Generate one image grounded in real reference photographs, via `POST /v1/images/edits`.

    `generate_image` is text-only: handed nothing but brand colours and a scene description, it can
    only invent a subject, which is the "random character images" failure this fixes — a
    photorealistic image, correctly styled, of a scene that has nothing to do with the client's
    actual business. This function instead downloads the real photographs Firecrawl found on the
    client's own page (`firecrawl_client.extract_reference_images`) and hands them to OpenAI as
    input alongside the prompt, so the output is a new image in the same visual register — same
    kind of subject, setting and mood — rather than an unconstrained guess.

    Raises `OpenAIImageError` if every reference URL fails to download, or if OpenAI's response has
    no usable image — callers (`image_briefs.generate_all`) fall back to `generate_image` on either.
    """
    if not reference_urls:
        raise OpenAIImageInvalidRequest("edit_image needs at least one entry in reference_urls.")
    if size not in VALID_SIZES:
        raise OpenAIImageInvalidRequest(
            f"{size!r} is not a size OpenAI's image models accept. Valid values: "
            f"{', '.join(sorted(VALID_SIZES))}."
        )
    if quality not in VALID_QUALITIES:
        raise OpenAIImageInvalidRequest(
            f"{quality!r} is not a quality OpenAI's image models accept. Valid values: "
            f"{', '.join(sorted(VALID_QUALITIES))}."
        )

    selected_model = model or os.environ.get(MODEL_ENV, DEFAULT_MODEL)

    downloaded: list[tuple[str, bytes, str]] = []
    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as downloader:
        for index, ref_url in enumerate(reference_urls[:_MAX_REFERENCE_IMAGES]):
            try:
                response = await downloader.get(ref_url)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                logger.warning("Could not download reference image %r for an edit: %s", ref_url, exc)
                continue
            content_type = response.headers.get("content-type", "image/png").split(";")[0].strip()
            extension = _CONTENT_TYPE_EXTENSIONS.get(content_type, "png")
            downloaded.append((f"reference-{index}.{extension}", response.content, content_type))

    if not downloaded:
        raise OpenAIImageError(
            f"None of the {len(reference_urls)} reference image(s) could be downloaded for an edit."
        )

    files = [("image[]", (name, data, content_type)) for name, data, content_type in downloaded]
    data_fields = {"model": selected_model, "prompt": prompt, "size": size, "quality": quality, "n": "1"}

    logger.info(
        "OpenAI Image API executing operation=edit model=%s size=%s references=%s/%s",
        selected_model,
        size,
        len(downloaded),
        len(reference_urls),
    )
    try:
        response = await _edit_client().post("/images/edits", data=data_fields, files=files)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("OpenAI Image API error operation=edit model=%s error=%s", selected_model, exc)
        raise _fail("Could not edit an image with OpenAI", exc) from exc

    payload_out = response.json()
    entries = payload_out.get("data") or []
    if not entries or not entries[0].get("b64_json"):
        logger.error("OpenAI Image API error operation=edit model=%s error=%s", selected_model, "response had no b64_json")
        raise OpenAIImageError("OpenAI returned no image data for this edit.")

    try:
        data = base64.b64decode(entries[0]["b64_json"])
    except (ValueError, TypeError) as exc:
        raise OpenAIImageError(f"OpenAI returned edited image data that could not be decoded: {exc}") from exc

    returned_format = payload_out.get("output_format") or DEFAULT_OUTPUT_FORMAT
    logger.info(
        "OpenAI Image API used operation=edit model=%s bytes=%s format=%s",
        selected_model,
        len(data),
        returned_format,
    )
    return GeneratedImageBytes(data=data, output_format=returned_format)
