"""Postgres-backed storage for files this backend generates and needs to hand out a URL for.

Why this exists
----------------
Every image this pipeline has referenced before now came pre-hosted: Context.dev's screenshots,
and originally Runway's generated images, both arrived as a URL on someone else's domain. OpenAI's
image models do not host anything — `openai_image_client.generate_image` returns raw bytes — so
something has to give those bytes a URL before a stage prompt can reference them the way
`design_md.py`'s logo section and `generation.py`'s `_generated_images_block` both already assume:
a short, reproducible link, not a value the model has to carry around itself.

**A base64 data URI is deliberately not that fix.** `design_md.py`'s logo section documents
exactly this failure already: a real image's data URI runs to thousands of characters the model
would have to echo byte-perfectly into its own output, which is what makes a generated page hit
its output cap mid-blob or draw a substitute instead. Handing the model a URL it copies once,
instead of a value it has to reproduce, is the whole fix.

Postgres, not local disk
-------------------------
The first version of this module wrote to local disk and served it via `StaticFiles`. That broke
on deployment: this app runs on Railway, where local disk is the *container's* disk — ephemeral
across every redeploy and restart by default. A Railway Volume would fix persistence, but Railway's
own docs are explicit that a Volume "cannot be used with replicas" and is capped at one per
service, so it would not survive this backend ever running as more than one instance either.

Postgres is already this app's durable, already-provisioned, already-multi-instance-safe system of
record, so the bytes go there instead — see `MediaAsset` in `app/db/models.py` for the table (the
one deliberate exception to this schema's usual "store a reference, not the bytes" rule — that
docstring explains why an OpenAI image specifically can't follow the `.pptx`
generate-on-demand-and-stream pattern the rest of this codebase uses for binary output) and
`app/routers/media.py` for the route that serves it back.
"""

from __future__ import annotations

import logging
import os
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import MediaAsset

logger = logging.getLogger(__name__)

PUBLIC_BASE_URL_ENV = "BACKEND_PUBLIC_URL"
#: Matches `app/__main__.py`'s own dev defaults (`DEFAULT_HOST`/`DEFAULT_PORT`) — not imported
#: from there, since that module is the process entrypoint, not something a service should depend
#: on; the two are kept in step by comment rather than by code. On a real deployment this must be
#: set explicitly (e.g. on Railway: `https://${{RAILWAY_PUBLIC_DOMAIN}}`) — the loopback default
#: below is unreachable from outside the container and would silently hand out dead links.
_DEFAULT_PUBLIC_BASE_URL = "http://127.0.0.1:8001"

MEDIA_URL_PREFIX = "/media"


def _public_base_url() -> str:
    return os.environ.get(PUBLIC_BASE_URL_ENV, "").strip() or _DEFAULT_PUBLIC_BASE_URL


def save_generated_image(session: AsyncSession, data: bytes, *, output_format: str) -> str:
    """Stage a `MediaAsset` row on `session` and return the absolute URL it will be served at.

    Does not commit — the caller's transaction does (see `image_briefs.generate_all`, which saves
    every successfully-generated image on the same session that then writes the run's
    `generated_images` context entry, so the two either land together or not at all). The id is
    assigned here, client-side, rather than left to a post-flush default: the URL has to be known
    immediately, before any flush happens.
    """
    asset_id = uuid.uuid4()
    session.add(MediaAsset(id=asset_id, data=data, content_type=f"image/{output_format.lstrip('.')}"))
    url = f"{_public_base_url().rstrip('/')}{MEDIA_URL_PREFIX}/{asset_id}"
    logger.info("Staged generated image bytes=%s url=%s", len(data), url)
    return url
