"""FastAPI application entrypoint for the Marketing-in-a-Box orchestrator API.

Run with (Windows-safe, see the event-loop note below):
    python -m app --reload

This module intentionally stays thin: it wires up the FastAPI app, app-wide middleware/config,
and mounts routers. Business logic belongs in app/services/, and persistence belongs in
app/db/ (owned by a separate pass) — routers here should only ever call into the service layer.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time
import warnings

from dotenv import load_dotenv

load_dotenv()

if sys.platform == "win32":
    # psycopg's async mode cannot run under Windows' ProactorEventLoop. The policy below is the
    # fix on uvicorn < 0.36; from 0.36 on, uvicorn hands `asyncio.run` an explicit `loop_factory`
    # (ProactorEventLoop on win32 unless it is spawning subprocesses), which ignores the policy
    # entirely — hence `app/__main__.py`, which builds the loop itself, and the fail-fast check in
    # `_verify_event_loop` below. Both the lookup and the call are deprecated as of Python 3.14, so
    # they sit inside the filter to keep that warning out of every startup log.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        _selector_policy = getattr(asyncio, "WindowsSelectorEventLoopPolicy", None)
        if _selector_policy is not None:
            asyncio.set_event_loop_policy(_selector_policy())

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.logging_config import configure_logging
from app.routers import anthropic, auth, chat_sessions, pipeline, usage

configure_logging()
logger = logging.getLogger(__name__)


def _verify_event_loop() -> None:
    """Refuse to serve on a loop psycopg can't use, instead of 500-ing every DB route.

    On Windows a ProactorEventLoop makes *every* database-backed endpoint fail at connect time
    (`psycopg.InterfaceError`) while `/health` and the docs keep answering 200 — which reads as
    "the backend is up, the feature is broken" (this is what silently emptied the chat-history
    sidebar). Fail at startup with the command that works instead.
    """
    if sys.platform != "win32":
        return
    loop_name = type(asyncio.get_running_loop()).__name__
    if "Proactor" not in loop_name:
        return
    raise RuntimeError(
        f"Started on {loop_name}, which psycopg's async mode cannot use, so every database route "
        "would fail with a 500. Launch the server with `python -m app --reload` (see "
        "app/__main__.py), or add --reload/--workers to your `uvicorn` command."
    )


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    _verify_event_loop()
    yield


app = FastAPI(
    title="Marketing-in-a-Box API",
    description=(
        "Orchestrator API for the Marketing-in-a-Box DAG pipeline: dependency-aware asset "
        "generation via the Anthropic Messages API, with a human-in-the-loop review gate."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# Dev-only CORS: the Vite dev server proxies /api/* to this backend (no browser CORS
# involved in that path), but this is kept so the frontend can also be pointed at the API
# directly (e.g. `vite preview`, or a different dev port) without a proxy in front of it.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str
    service: str


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check() -> HealthResponse:
    """Liveness/readiness probe. Does not touch the database or Redis — those get their own
    dedicated checks once app/db/ and the Celery worker wiring land."""
    return HealthResponse(status="ok", service="marketing-in-a-box-backend")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every API hit — method, path, status, and duration — for bug/traffic tracking."""
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s -> %s (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(anthropic.router, prefix="/test/anthropic", tags=["anthropic-test"])
app.include_router(pipeline.router, prefix="/pipeline", tags=["pipeline"])
app.include_router(chat_sessions.router, prefix="/chat-sessions", tags=["chat-sessions"])
app.include_router(usage.router, prefix="/usage", tags=["usage"])

# Feature routers are mounted here as they land, e.g.:
#   from app.routers import runs
#   app.include_router(runs.router, prefix="/runs", tags=["runs"])
