"""Tests for `app/services/image_briefs.py`.

The regression this file exists to prevent: when this module talked to Runway, every ratio it
emitted was one `runway_client.generate_image` would 400 on — the ratio strings simply weren't in
Runway's accepted enum, and no mocked test caught it because nothing cross-checked the two modules
against each other; only a live call did. `test_every_brief_size_is_one_openai_actually_accepts`
is that cross-check for the OpenAI wiring, kept permanently for the same reason.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from app.services import design_md, image_briefs, media_storage, openai_image_client, runway_image_client
from app.services.design_tokens import DesignTokens

URL = "https://trafficradius.com.au/"


@dataclass
class _FakeSession:
    """The one method `media_storage.save_generated_image` actually calls."""

    added: list[Any] = field(default_factory=list)

    def add(self, obj: Any) -> None:
        self.added.append(obj)


def _design_md_sample() -> str:
    return design_md.build_design_md(
        URL,
        None,
        None,
        DesignTokens(source_url=URL, available=True),
        fallback=design_md.BrandFallback(
            source="firecrawl", primary="#a4d36b", background="#ffffff", on_surface="#3d3d3d", body_font="Montserrat"
        ),
    )


def test_every_brief_size_is_one_openai_actually_accepts():
    briefs = image_briefs.build_image_briefs(_design_md_sample())
    for brief in briefs:
        assert brief.size in openai_image_client.VALID_SIZES, (
            f"{brief.role} brief uses size {brief.size!r}, which OpenAI's image models reject"
        )


def test_briefs_cover_hero_proof_and_closing_cta():
    roles = {brief.role for brief in image_briefs.build_image_briefs(_design_md_sample())}
    assert roles == {"hero", "proof", "closing-cta"}


def test_brief_prompts_bind_to_the_measured_brand_tokens():
    document = _design_md_sample()
    briefs = image_briefs.build_image_briefs(document)

    for brief in briefs:
        assert "#a4d36b" in brief.prompt
        assert "#ffffff" in brief.prompt
        assert "Montserrat" in brief.prompt


def test_brief_prompts_forbid_the_usual_ai_image_tells():
    for brief in image_briefs.build_image_briefs(_design_md_sample()):
        lowered = brief.prompt.lower()
        assert "do not add logos" in lowered
        assert "watermarks" in lowered


@pytest.mark.asyncio
async def test_generate_all_is_a_no_op_when_openai_is_not_configured(monkeypatch):
    """No key, no delay, no log noise — the same 'skip cleanly' contract every other optional
    source in this codebase has (`context_dev.is_configured()`, `firecrawl_client`, ...)."""
    monkeypatch.setattr(openai_image_client, "is_configured", lambda: False)
    monkeypatch.setattr(runway_image_client, "is_configured", lambda: False)
    briefs = image_briefs.build_image_briefs(_design_md_sample())

    generated, notes = await image_briefs.generate_all(briefs, _FakeSession())

    assert generated == ()
    assert notes == ()


@pytest.mark.asyncio
async def test_generate_all_fulfils_each_brief_independently(monkeypatch):
    """One brief failing (a content-policy rejection, an out-of-credits response partway through)
    must not cost the other two — each is its own note, not a shared failure."""
    monkeypatch.setattr(openai_image_client, "is_configured", lambda: True)
    # Runway unconfigured, so the failed brief's note reports the real OpenAI error rather than a
    # Runway fallback attempt (which, left unmocked, would otherwise make a real network call).
    monkeypatch.setattr(runway_image_client, "is_configured", lambda: False)

    async def fake_generate(prompt, *, size, **_):
        if "Proof section" in prompt:
            raise openai_image_client.OpenAIImageError("content_policy_violation")
        return openai_image_client.GeneratedImageBytes(data=b"fake-bytes", output_format="png")

    monkeypatch.setattr(openai_image_client, "generate_image", fake_generate)
    briefs = image_briefs.build_image_briefs(_design_md_sample())
    session = _FakeSession()

    generated, notes = await image_briefs.generate_all(briefs, session)

    assert {g.role for g in generated} == {"hero", "closing-cta"}
    assert all(g.url.startswith(media_storage._public_base_url()) for g in generated)
    assert len(session.added) == 2  # the two that succeeded, staged on the session
    assert len(notes) == 1
    assert "proof" in notes[0].lower()
    assert "content_policy_violation" in notes[0].lower()


@pytest.mark.asyncio
async def test_a_save_failure_is_also_a_note_not_a_crash(monkeypatch):
    """OpenAI can succeed and the Postgres write can still fail — that should degrade the same
    way a generation failure does, not raise out of `generate_all`."""
    monkeypatch.setattr(openai_image_client, "is_configured", lambda: True)

    async def fake_generate(prompt, *, size, **_):
        return openai_image_client.GeneratedImageBytes(data=b"fake-bytes", output_format="png")

    def fake_save(_session, _data, *, output_format):
        raise RuntimeError("connection to the database was lost")

    monkeypatch.setattr(openai_image_client, "generate_image", fake_generate)
    monkeypatch.setattr(media_storage, "save_generated_image", fake_save)
    briefs = image_briefs.build_image_briefs(_design_md_sample())

    generated, notes = await image_briefs.generate_all(briefs, _FakeSession())

    assert generated == ()
    assert len(notes) == 3
    assert all("could not be saved" in note.lower() for note in notes)


def test_subject_context_is_bound_into_every_brief():
    """The fix for 'random character images' that don't reflect the client's business: without a
    subject, the model had nothing but colours to go on and filled the gap with an arbitrary scene.
    `subject_context` is that missing grounding."""
    briefs = image_briefs.build_image_briefs(_design_md_sample(), subject_context="SEO for e-commerce stores")
    for brief in briefs:
        assert "SEO for e-commerce stores" in brief.prompt


def test_no_subject_context_still_gets_a_neutral_grounding_instruction():
    """Absent a subject, the prompt must still say something that stops the model inventing a
    specific unrelated business — not silently fall back to the old ungrounded wording."""
    briefs = image_briefs.build_image_briefs(_design_md_sample())
    for brief in briefs:
        assert "industry-neutral" in brief.prompt.lower()


def test_reference_image_urls_are_carried_onto_every_brief():
    refs = ("https://trafficradius.com.au/hero.jpg", "https://trafficradius.com.au/team.jpg")
    briefs = image_briefs.build_image_briefs(_design_md_sample(), reference_image_urls=refs)
    for brief in briefs:
        assert brief.reference_image_urls == refs
        assert "real photographs from this client" in brief.prompt.lower()


@pytest.mark.asyncio
async def test_generate_all_grounds_a_brief_with_reference_images_via_edit(monkeypatch):
    """A brief carrying reference photos must be fulfilled through `edit_image`, not a text-only
    `generate_image` call — that is the whole point of scraping them."""
    monkeypatch.setattr(openai_image_client, "is_configured", lambda: True)
    monkeypatch.setattr(runway_image_client, "is_configured", lambda: False)

    calls = []

    async def fake_edit(prompt, reference_urls, *, size, **_):
        calls.append(reference_urls)
        return openai_image_client.GeneratedImageBytes(data=b"fake-bytes", output_format="png")

    async def fake_generate(prompt, *, size, **_):
        raise AssertionError("should not fall back to a text-only generation when refs are given")

    monkeypatch.setattr(openai_image_client, "edit_image", fake_edit)
    monkeypatch.setattr(openai_image_client, "generate_image", fake_generate)

    refs = ("https://trafficradius.com.au/hero.jpg",)
    briefs = image_briefs.build_image_briefs(_design_md_sample(), reference_image_urls=refs)

    generated, notes = await image_briefs.generate_all(briefs, _FakeSession())

    assert len(generated) == 3
    assert notes == ()
    assert calls == [refs] * 3


@pytest.mark.asyncio
async def test_generate_all_falls_back_to_text_only_when_the_edit_fails(monkeypatch):
    """A reference URL that has gone stale, or a content-policy rejection on the edit, must not
    lose the image outright — it should still get a plain, ungrounded generation."""
    monkeypatch.setattr(openai_image_client, "is_configured", lambda: True)
    monkeypatch.setattr(runway_image_client, "is_configured", lambda: False)

    async def fake_edit(prompt, reference_urls, *, size, **_):
        raise openai_image_client.OpenAIImageError("could not download reference image")

    async def fake_generate(prompt, *, size, **_):
        return openai_image_client.GeneratedImageBytes(data=b"fake-bytes", output_format="png")

    monkeypatch.setattr(openai_image_client, "edit_image", fake_edit)
    monkeypatch.setattr(openai_image_client, "generate_image", fake_generate)

    refs = ("https://trafficradius.com.au/hero.jpg",)
    briefs = image_briefs.build_image_briefs(_design_md_sample(), reference_image_urls=refs)

    generated, notes = await image_briefs.generate_all(briefs, _FakeSession())

    assert len(generated) == 3
    assert notes == ()


def test_missing_tokens_fall_back_to_a_named_placeholder_not_a_blank():
    """No design system at all (a page with no readable brand) should still describe *something*
    identifiable as a fallback, not silently drop the clause and leave the prompt looking measured
    when it is not."""
    unavailable = design_md._unavailable_md(URL, "no reader answered")
    briefs = image_briefs.build_image_briefs(unavailable)

    for brief in briefs:
        assert "the measured" in brief.prompt
