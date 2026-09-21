"""Server-side Runway image generation through the current REST API."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

API_KEY_ENV = "RUNWAYML_API_SECRET"
MODEL_ENV = "RUNWAY_IMAGE_MODEL"
BASE_URL = "https://api.dev.runwayml.com"
API_VERSION = "2024-11-06"
POLL_INTERVAL_SECONDS = 5.0
MAX_POLL_SECONDS = 300.0


class RunwayError(Exception):
    """A Runway request failed or returned an unusable task."""


class RunwayNotConfigured(RunwayError):
    """The Runway API key is not configured."""


def is_configured() -> bool:
    return bool(os.environ.get(API_KEY_ENV, "").strip())


def _headers() -> dict[str, str]:
    key = os.environ.get(API_KEY_ENV, "").strip()
    if not key:
        raise RunwayNotConfigured(
            f"{API_KEY_ENV} is not set. Add the Runway API key to the backend .env."
        )
    return {
        "Authorization": f"Bearer {key}",
        "X-Runway-Version": API_VERSION,
        "Content-Type": "application/json",
    }


def _error(response: httpx.Response, operation: str) -> RunwayError:
    try:
        payload = response.json()
        detail = payload.get("error") or payload.get("message") or payload
    except ValueError:
        detail = response.text[:300]
    return RunwayError(f"Runway {operation} failed with HTTP {response.status_code}: {detail}")


async def generate_image(
    prompt: str,
    *,
    ratio: str = "1360:768",
    model: str | None = None,
    output_count: int = 1,
) -> tuple[str, ...]:
    """Generate GPT Image 2-compatible output and return hosted image URLs."""
    selected_model = model or os.environ.get(MODEL_ENV, "gpt_image_2")
    payload: dict[str, Any] = {
        "model": selected_model,
        "promptText": prompt,
        "ratio": ratio,
    }
    if output_count > 1:
        payload["outputCount"] = min(output_count, 10)

    logger.info(
        "Runway API executing operation=text_to_image model=%s ratio=%s output_count=%s",
        selected_model,
        ratio,
        output_count,
    )
    try:
        async with httpx.AsyncClient(base_url=BASE_URL, headers=_headers(), timeout=60.0) as client:
            response = await client.post("/v1/text_to_image", json=payload)
            if response.is_error:
                raise _error(response, "text_to_image")
            task = response.json()
            task_id = task.get("id")
            if not task_id:
                raise RunwayError("Runway did not return a task id for text_to_image.")
            urls = await _wait_for_task(client, task_id)
    except Exception as exc:
        logger.error("Runway API error operation=text_to_image model=%s error=%s", selected_model, exc)
        raise

    logger.info("Runway API used operation=text_to_image model=%s images=%s", selected_model, len(urls))
    return urls


async def _wait_for_task(client: httpx.AsyncClient, task_id: str) -> tuple[str, ...]:
    elapsed = 0.0
    while elapsed <= MAX_POLL_SECONDS:
        response = await client.get(f"/v1/tasks/{task_id}")
        if response.is_error:
            raise _error(response, f"task_poll task_id={task_id}")
        task = response.json()
        status = task.get("status")
        if status == "SUCCEEDED":
            output = task.get("output") or []
            urls = tuple(str(item) for item in output if item)
            if not urls:
                raise RunwayError(f"Runway task {task_id} succeeded without image URLs.")
            return urls
        if status in {"FAILED", "CANCELED", "ABORTED"}:
            raise RunwayError(f"Runway task {task_id} ended with status {status}.")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
        elapsed += POLL_INTERVAL_SECONDS
    raise RunwayError(f"Runway task {task_id} did not finish within {int(MAX_POLL_SECONDS)}s.")
