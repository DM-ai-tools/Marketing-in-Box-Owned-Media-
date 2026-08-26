"""Thin async wrapper around the Anthropic Messages API.

Mirrors the lazy env-read pattern in app/db/base.py: `ANTHROPIC_API_KEY` is read from the
environment on first use (inside `get_client()`), not at import time, so importing this
module never requires the key to be set. All other services that need to call Claude should
go through `get_client()` rather than constructing their own `AsyncAnthropic` instance, so the
process keeps a single pooled client.
"""

from __future__ import annotations

import logging
import os
from dotenv import load_dotenv

load_dotenv()

from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)

_client: AsyncAnthropic | None = None


def anthropic_api_key() -> str:
    """Read `ANTHROPIC_API_KEY` from the environment, raising a clear error if unset."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Copy application/backend/.env.example to .env and "
            "set a real Anthropic API key."
        )
    return key


def get_client() -> AsyncAnthropic:
    """Return the process-wide async Anthropic client, creating it on first use."""
    global _client
    if _client is None:
        logger.info("Initializing Anthropic client")
        _client = AsyncAnthropic(api_key=anthropic_api_key())
    return _client
