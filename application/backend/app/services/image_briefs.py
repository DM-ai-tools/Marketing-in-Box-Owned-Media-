"""Brand-aware image briefs for HTML-producing assets, and the OpenAI calls that fulfil them.

Why generation happens here and not in the model's own prompt
----------------------------------------------------------------
A brief used to be handed to the model as an instruction — "generate this with Runway, then place
the returned URL in the HTML" — inside the HTML-producing stage's own prompt. That call has no tool
access to an image generator, so the instruction was unfollowable: the model could only fabricate a
plausible-looking URL, exactly the failure `design_tokens.py` documents for an invented palette,
one layer up. `generate_all` is the fix — the same shape as that fix, too: measure first, then hand
the model the real, already-resolved value, never an instruction to produce one itself.

Runway -> OpenAI
----------------
Originally wired to Runway, which hosts the image it generates and returns a URL. OpenAI's image
models return base64 bytes instead (confirmed against OpenAI's own docs before switching:
`response_format=url` is DALL-E-only), so `generate_all` now does one more step than it used to —
`media_storage.save_generated_image` stages those bytes as a `MediaAsset` row and returns the URL
this backend serves them back at. See that module's docstring for why a data URI is not the fix,
and why the bytes land in Postgres rather than on local disk (this app deploys to Railway, where
local disk is the container's own ephemeral disk).
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import media_storage, openai_image_client

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ImageBrief:
    role: str
    size: str
    prompt: str


@dataclass(frozen=True)
class GeneratedImage:
    """One brief, fulfilled. `url` is this backend's own `/media/generated/...` — see
    `media_storage.py` for why the bytes OpenAI returns end up there rather than inline."""

    role: str
    size: str
    prompt: str
    url: str


def _token(document: str, name: str, fallback: str) -> str:
    match = re.search(rf"^\s+{re.escape(name)}:\s+[\"']?([^\"'\n]+)", document, re.MULTILINE)
    return match.group(1).strip() if match else fallback


def build_image_briefs(design_md: str, *, asset_label: str = "the HTML asset") -> tuple[ImageBrief, ...]:
    """Create prompts that bind subject matter to the measured brand system."""
    primary = _token(design_md, "primary", "the measured primary brand colour")
    surface = _token(design_md, "surface", "the measured surface colour")
    ink = _token(design_md, "on-surface", "the measured text colour")
    heading_font = _token(design_md, "fontFamily", "the measured heading typeface")
    base = (
        f"Photorealistic editorial image for {asset_label}. Match the brand system exactly: "
        f"primary accent {primary}, surface {surface}, text contrast {ink}, typography reference {heading_font}. "
        "Use natural light, believable human expression, realistic skin and materials, premium commercial photography, "
        "restrained composition, and intentional negative space for HTML overlay text. Do not add logos, watermarks, "
        "legible text, fake UI, gradients, illustration, or generic stock-photo styling."
    )
    return (
        ImageBrief(
            role="hero",
            # The widest of OpenAI's three named GPT-image sizes — the hero band a landing page
            # composes against is wide, not square. See `openai_image_client.VALID_SIZES`.
            size="1536x1024",
            prompt=f"{base} Hero composition: a credible scene that communicates the service outcome, with the focal subject on the right and clean copy space on the left.",
        ),
        ImageBrief(
            role="proof",
            # Square — a proof/testimonial card crops far more forgivingly than a wide hero shot.
            size="1024x1024",
            prompt=f"{base} Proof section composition: a specific, grounded moment showing the client or customer experiencing the measurable outcome, with room for a short heading and caption.",
        ),
        ImageBrief(
            role="closing-cta",
            size="1536x1024",
            prompt=f"{base} Closing call-to-action composition: confident but human, visually calm, with a clear foreground subject and generous uncluttered space for a CTA overlay.",
        ),
    )


async def generate_all(
    briefs: tuple[ImageBrief, ...], session: AsyncSession
) -> tuple[tuple[GeneratedImage, ...], tuple[str, ...]]:
    """Fulfil every brief through OpenAI and return `(generated, notes)`.

    The OpenAI calls are issued concurrently, like the two Context.dev screenshots in
    `design_md.capture_page_design`, and each is allowed to fail on its own: three independent
    images, so a content-policy rejection on one does not cost the other two.

    Saving to Postgres happens *after* that gather, one at a time — an `AsyncSession` is not safe
    for concurrent use across coroutines, so `media_storage.save_generated_image` cannot be called
    from inside the concurrent branch. This only adds a handful of in-process `session.add()` calls
    to the critical path, not more network round trips: nothing is flushed or committed here,
    so `session.add()` is not itself awaited. The caller (`_ensure_generated_images` in
    `app/routers/pipeline.py`) commits once, after also writing the run's `generated_images`
    context entry on the same session — the images and the pointer to them land together or not
    at all.

    `notes` carries one line per failure for the caller to fold into the run's own notes — the
    same "state it, don't invent a substitute" rule as everywhere else this pipeline degrades.

    Returns `((), ())` immediately when OpenAI is not configured, so a deployment with no key
    behaves exactly as it did before this function existed — no delay, no log noise.
    """
    if not briefs or not openai_image_client.is_configured():
        return (), ()

    async def _one(brief: ImageBrief) -> openai_image_client.GeneratedImageBytes | Exception:
        try:
            return await openai_image_client.generate_image(brief.prompt, size=brief.size)
        except openai_image_client.OpenAIImageError as exc:
            return exc

    results = await asyncio.gather(*(_one(brief) for brief in briefs))

    generated: list[GeneratedImage] = []
    notes: list[str] = []
    for brief, result in zip(briefs, results):
        if isinstance(result, Exception):
            logger.info("Image brief %r could not be fulfilled: %s", brief.role, result)
            notes.append(f"The {brief.role} image could not be generated: {result}")
            continue
        try:
            url = media_storage.save_generated_image(session, result.data, output_format=result.output_format)
        except Exception as exc:  # noqa: BLE001 - degrades like any other brief failure, not fatal
            logger.info("Image brief %r generated but could not be saved: %s", brief.role, exc)
            notes.append(f"The {brief.role} image could not be saved: {exc}")
            continue
        generated.append(GeneratedImage(role=brief.role, size=brief.size, prompt=brief.prompt, url=url))

    logger.info(
        "Image briefs fulfilled=%s/%s roles=%s",
        len(generated),
        len(briefs),
        ",".join(g.role for g in generated) or "none",
    )
    return tuple(generated), tuple(notes)
