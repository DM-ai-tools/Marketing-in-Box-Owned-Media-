"""`python -m app` — the supported way to start the API server.

Why this exists instead of a bare `uvicorn app.main:app`:

uvicorn >= 0.36 no longer consults `asyncio`'s event-loop policy. It resolves a `loop_factory`
itself and passes it to `asyncio.run`, and on win32 that factory is `ProactorEventLoop` unless
uvicorn happens to be spawning subprocesses (`--reload` / `--workers`). psycopg's async mode
refuses to run on a ProactorEventLoop, so a plain single-process `uvicorn app.main:app` on Windows
serves `/health` and `/docs` fine while every database-backed route fails with a 500 — the failure
mode that made the chat-history sidebar look permanently empty.

The loop factory can only be overridden by the process that calls `asyncio.run`, which is why the
fix lives in a launcher rather than in `app/main.py`.

Usage:
    python -m app --reload                  # dev (default host 127.0.0.1, port 8001)
    python -m app --host 0.0.0.0 --port 80  # anything `uvicorn.Config` accepts
"""

from __future__ import annotations

import argparse
import asyncio
import selectors
import sys
from collections.abc import Callable

import uvicorn

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8001


def _loop_factory() -> Callable[[], asyncio.AbstractEventLoop] | None:
    """A psycopg-compatible loop factory on Windows; uvicorn's own default elsewhere."""
    if sys.platform != "win32":
        return None
    return lambda: asyncio.SelectorEventLoop(selectors.SelectSelector())


def _serve(config: uvicorn.Config) -> None:
    """Run a single-process server on a loop we choose, not the one uvicorn would pick."""
    server = uvicorn.Server(config)
    factory = _loop_factory()
    if factory is None:
        server.run()
        return

    try:
        asyncio.run(server.serve(), loop_factory=factory)  # type: ignore[call-arg]  # 3.12+
    except TypeError:
        # Python 3.11 has no `loop_factory=`; drive the loop by hand instead.
        loop = factory()
        try:
            loop.run_until_complete(server.serve())
        finally:
            loop.close()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m app", description="Run the Marketing-in-a-Box API.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--reload", action="store_true", help="Restart on source changes (dev).")
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--log-level", default=None)
    args = parser.parse_args(argv)

    config = uvicorn.Config(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers,
        log_level=args.log_level,
    )

    if config.should_reload or config.workers > 1:
        # These paths run the app in a subprocess, and uvicorn already picks a SelectorEventLoop
        # for those — so hand them straight back to uvicorn's own supervisor.
        uvicorn.run(
            "app.main:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            workers=args.workers,
            log_level=args.log_level,
        )
        return

    _serve(config)


if __name__ == "__main__":
    main()
