"""RunwayML text-to-image client — fallback when OpenAI image generation fails.

Shape mirrors `openai_image_client` deliberately: both expose `is_configured()`,
`generate_image(prompt, *, size) -> GeneratedImageBytes`, and the same error hierarchy.
`image_briefs.generate_all` and `pipeline.generate_design_image` can call either
interchangeably — they only import the shared `GeneratedImageBytes` dataclass from
`openai_image_client` (Runway re-exports it from there so nothing else changes).

Key differences from OpenAI
-----------------------------
* **Async task, not synchronous.** Runway's text_to_image endpoint returns a task id;
  we poll `GET /v1/tasks/{id}` until it is SUCCEEDED or FAILED. Polling uses exponential
  back-off up to `_POLL_MAX_WAIT_SECONDS`.
* **URL, not bytes.** Runway hosts the generated image and returns a signed URL.
  We download the bytes from that URL so `media_storage.save_generated_image` can
  store them in Postgres exactly as it does for OpenAI output.
* **Aspect ratio, not pixel size.** Runway accepts "16:9" / "9:16" / "1:1" instead of
  "WxH". `_openai_size_to_ratio` converts the OpenAI size string callers pass in.

Testing
-------
Patch `generate_image` directly in tests — never `_client()`.

Docs
----
* Python SDK     https://github.com/runwayml/sdk-python
* API reference  https://docs.dev.runwayml.com/
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from functools import lru_cache

import httpx

# Re-use the same result dataclass so callers are provider-agnostic.
from app.services.openai_image_client import GeneratedImageBytes

logger = logging.getLogger(__name__)

API_KEY_ENV = "RUNWAYML_API_SECRET"
BASE_URL = "https://api.dev.runwayml.com"
API_VERSION = "2024-11-06"
DEFAULT_MODEL = "gen4_image"

_TIMEOUT_SECONDS = 60.0        # per HTTP call (not total task time)
_POLL_INTERVAL_SECONDS = 3.0   # initial poll interval
_POLL_BACKOFF_FACTOR = 1.5     # multiply interval after each poll
_POLL_MAX_WAIT_SECONDS = 120.0 # give up after this many seconds total

# Map OpenAI WxH strings -> Runway aspect-ratio strings.
_SIZE_TO_RATIO: dict[str, str] = {
    "1536x1024": "3:2",
    "1024x1536": "2:3",
    "1024x1024": "1:1",
    "auto": "16:9",
}
DEFAULT_RATIO = "16:9"


class RunwayImageError(Exception):
    """A Runway image request failed or returned an unusable response."""


class RunwayImageNotConfigured(RunwayImageError):
    """`RUNWAYML_API_SECRET` is not set. Callers treat this as 'skip me'."""


class RunwayImageTaskFailed(RunwayImageError):
    """The Runway task completed with a FAILED status."""


def is_configured() -> bool:
    return bool(os.environ.get(API_KEY_ENV, "").strip())


@lru_cache(maxsize=1)
def _client() -> httpx.AsyncClient:
    """Shared async client — cached so the connection pool is reused."""
    key = os.environ.get(API_KEY_ENV, "").strip()
    if not key:
        raise RunwayImageNotConfigured(
            f"{API_KEY_ENV} is not set, so Runway image generation is unavailable."
        )
    return httpx.AsyncClient(
        base_url=BASE_URL,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "X-Runway-Version": API_VERSION,
        },
        timeout=_TIMEOUT_SECONDS,
    )


def reset_client() -> None:
    """Drop the cached client. For tests and for a key rotated without a restart."""
    _client.cache_clear()


def _openai_size_to_ratio(size: str) -> str:
    """Convert an OpenAI 'WxH' size string to a Runway aspect-ratio string."""
    return _SIZE_TO_RATIO.get(size, DEFAULT_RATIO)


async def _poll_until_done(task_id: str) -> list[str]:
    """Poll the task endpoint until it succeeds or fails.

    Returns the list of output URLs on success.
    Raises `RunwayImageTaskFailed` on failure or timeout.
    """
    client = _client()
    deadline = time.monotonic() + _POLL_MAX_WAIT_SECONDS
    interval = _POLL_INTERVAL_SECONDS

    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RunwayImageTaskFailed(
                f"Runway task {task_id!r} did not complete within "
                f"{int(_POLL_MAX_WAIT_SECONDS)}s."
            )

        await asyncio.sleep(interval)

        try:
            resp = await client.get(f"/v1/tasks/{task_id}")
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            # Transient network errors — keep polling.
            logger.warning("Runway poll error task_id=%s error=%s", task_id, exc)
            interval = min(interval * _POLL_BACKOFF_FACTOR, remaining)
            continue

        body = resp.json()
        status = body.get("status", "")

        if status == "SUCCEEDED":
            outputs: list[str] = body.get("output") or []
            if not outputs:
                raise RunwayImageTaskFailed(
                    f"Runway task {task_id!r} SUCCEEDED but returned no output URLs."
                )
            logger.info("Runway task SUCCEEDED task_id=%s urls=%s", task_id, len(outputs))
            return outputs

        if status == "FAILED":
            failure = body.get("failure") or body.get("failureCode") or "unknown reason"
            raise RunwayImageTaskFailed(f"Runway task {task_id!r} FAILED: {failure}")

        # PENDING / THROTTLED / RUNNING — keep waiting.
        logger.debug("Runway task status=%s task_id=%s", status, task_id)
        interval = min(interval * _POLL_BACKOFF_FACTOR, max(remaining, 1))


async def _download_image(url: str) -> bytes:
    """Download image bytes from a Runway-hosted signed URL."""
    # Plain client (no auth headers) — Runway signed URLs are self-contained.
    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as dl:
        try:
            resp = await dl.get(url, follow_redirects=True)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise RunwayImageError(
                f"Could not download Runway image from {url!r}: {exc}"
            ) from exc
    return resp.content


async def generate_image(
    prompt: str,
    *,
    size: str = "1536x1024",
) -> GeneratedImageBytes:
    """Generate one image via Runway and return its raw bytes.

    `size` accepts the same OpenAI WxH strings used throughout this pipeline;
    converted to the nearest Runway aspect-ratio internally.
    """
    client = _client()  # raises RunwayImageNotConfigured if key is missing

    ratio = _openai_size_to_ratio(size)
    logger.info(
        "Runway Image API executing operation=generate model=%s ratio=%s",
        DEFAULT_MODEL,
        ratio,
    )

    try:
        resp = await client.post(
            "/v1/text_to_image",
            json={
                "model": DEFAULT_MODEL,
                "promptText": prompt,
                "ratio": ratio,
            },
        )
        resp.raise_for_status()
    except httpx.TimeoutException as exc:
        raise RunwayImageError(
            f"Runway did not answer within {int(_TIMEOUT_SECONDS)}s."
        ) from exc
    except httpx.ConnectError as exc:
        raise RunwayImageError("Could not reach Runway from this server.") from exc
    except httpx.HTTPStatusError as exc:
        try:
            detail = exc.response.json()
        except ValueError:
            detail = exc.response.text[:300]
        raise RunwayImageError(
            f"Runway answered HTTP {exc.response.status_code}: {detail}"
        ) from exc

    task_id: str = resp.json().get("id", "")
    if not task_id:
        raise RunwayImageError("Runway returned no task id.")

    logger.info("Runway task created task_id=%s", task_id)
    output_urls = await _poll_until_done(task_id)
    data = await _download_image(output_urls[0])

    # Guess format from URL; default to png.
    url_lower = output_urls[0].lower()
    if ".jpg" in url_lower or ".jpeg" in url_lower:
        output_format = "jpeg"
    elif ".webp" in url_lower:
        output_format = "webp"
    else:
        output_format = "png"

    logger.info(
        "Runway Image API used operation=generate bytes=%s format=%s",
        len(data),
        output_format,
    )
    return GeneratedImageBytes(data=data, output_format=output_format)
