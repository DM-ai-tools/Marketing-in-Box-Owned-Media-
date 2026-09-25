"""Tests for `app/routers/pipeline.py`'s `_image_subject_context`.

Why this exists
----------------
`image_briefs.build_image_briefs` used to have nothing but brand colours to brief a generated
hero/proof/CTA image on, which is how it produced photorealistic images of an arbitrary, unrelated
scene — the "random character images" bug. `_image_subject_context` is what pulls a real, already-
on-hand description of the client's business out of the stage's own intake, so the brief can be
grounded in it instead. See `app/services/image_briefs.py` and `design_md.py`'s `capture_page_design`.
"""

from __future__ import annotations


def test_prefers_the_stage_s_own_service_field():
    from app.routers.pipeline import _image_subject_context

    answers = {
        "target_service_or_sub_service": "Meta Ads for e-commerce brands",
        "client_industry": "Digital marketing",
    }
    assert _image_subject_context(answers, {}) == "Meta Ads for e-commerce brands — Digital marketing"


def test_falls_back_to_the_run_level_profile_when_the_stage_has_nothing():
    from app.routers.pipeline import _image_subject_context

    profile = {"industry": "SEO for e-commerce stores"}
    assert _image_subject_context({}, profile) == "SEO for e-commerce stores"


def test_placeholder_sentinels_are_excluded():
    """A field left unanswered (`N/A`, `NONE`, blank) must not become the image's business
    description — that would brief the generator on the literal placeholder word."""
    from app.routers.pipeline import _image_subject_context

    answers = {
        "target_service_or_sub_service": "N/A",
        "client_industry": "NONE",
        "sub_vertical_niche": "",
    }
    assert _image_subject_context(answers, {"industry": "UNKNOWN"}) == ""


def test_duplicate_values_are_not_repeated():
    from app.routers.pipeline import _image_subject_context

    answers = {"client_industry": "Roofing"}
    profile = {"industry": "Roofing"}
    assert _image_subject_context(answers, profile) == "Roofing"


def test_context_reference_placeholders_are_excluded():
    """`[[context:...]]` is an unresolved reference token, not a real answer — the same rule
    `_design_source_url` already applies to the design-source fields."""
    from app.routers.pipeline import _image_subject_context

    answers = {"target_service_or_sub_service": "[[context:icp_document]]"}
    assert _image_subject_context(answers, {}) == ""
