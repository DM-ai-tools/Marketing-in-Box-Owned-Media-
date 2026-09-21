"""Brand-aware image briefs for HTML-producing assets."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ImageBrief:
    role: str
    ratio: str
    prompt: str


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
            ratio="1360:768",
            prompt=f"{base} Hero composition: a credible scene that communicates the service outcome, with the focal subject on the right and clean copy space on the left.",
        ),
        ImageBrief(
            role="proof",
            ratio="1168:880",
            prompt=f"{base} Proof section composition: a specific, grounded moment showing the client or customer experiencing the measurable outcome, with room for a short heading and caption.",
        ),
        ImageBrief(
            role="closing-cta",
            ratio="1360:768",
            prompt=f"{base} Closing call-to-action composition: confident but human, visually calm, with a clear foreground subject and generous uncluttered space for a CTA overlay.",
        ),
    )


def briefs_markdown(briefs: tuple[ImageBrief, ...]) -> str:
    lines = [
        "## Image generation briefs",
        "",
        "Use these briefs with Runway GPT Image 2 (`gpt_image_2`) when the HTML asset needs branded imagery. "
        "Keep the returned image URL in the generated HTML; do not embed base64 output or invent a substitute image.",
        "",
    ]
    for index, brief in enumerate(briefs, start=1):
        lines.extend(
            [
                f"### {index}. {brief.role}",
                f"- **Aspect ratio**: `{brief.ratio}`",
                f"- **Prompt**: {brief.prompt}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()
