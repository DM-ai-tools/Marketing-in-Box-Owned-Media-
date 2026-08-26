"""Central logging configuration for the Marketing-in-a-Box backend.

Call `configure_logging()` once, at process start (from `app.main`, before the FastAPI app is
built), so every module's `logging.getLogger(__name__)` call shares one format, level, and
output stream. Reads `LOG_LEVEL` from the environment (default `INFO`) so verbosity can be
raised (e.g. to `DEBUG`) without a code change — set it in `.env` alongside `ANTHROPIC_API_KEY`.
"""

from __future__ import annotations

import logging
import os

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def configure_logging() -> None:
    """Configure the root logger. Safe to call more than once (e.g. under `--reload`)."""
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(level=level, format=_LOG_FORMAT, force=True)
