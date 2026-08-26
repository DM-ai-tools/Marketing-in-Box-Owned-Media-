"""Tests for the reference-library injection in `app/services/generation.py`.

The bug worth guarding here failed *silently*. `COMPREHENSIVE_HEADLINE_FRAMEWORK.md` is converted
from a PDF whose fonts are subsetted and Identity-encoded; a converter that ignores the PDF's
/ToUnicode CMaps maps every digit glyph to U+00FD, so the file still reads as fluent English while
every number in it has been destroyed — including the per-channel character limits that are the only
reason two of the Value Ladder prompt's headline rules can be followed at all. Nothing downstream
can detect that, so it is asserted here instead.

The second thing pinned is the *ordering* inside `build_prompt`. Each master prompt ends by telling
the model to proceed; a 44KB reference document appended after that instruction would bury it.
"""

from __future__ import annotations

import pytest

from app.services.generation import (
    HEADLINE_FRAMEWORK,
    PHASE2_STAGE_CONFIGS,
    REFERENCE_LIBRARY,
    STAGE_CONFIGS,
    CorruptReferenceDocError,
    _load_reference_library,
    _PROMPTS_DIR,
    _validate_reference_doc,
    build_prompt,
)

# The limits Rule 4 of the Value Ladder prompt points at, and the reason the reconversion happened.
# Each was "yy characters" in the ToUnicode-blind conversion.
EXPECTED_LIMITS = [
    "30 characters per headline",
    "25 characters maximum",
    "25-40 characters",
    "50-60 characters",
    "60-80 characters",
]


@pytest.fixture(scope="module")
def framework_text() -> str:
    return (_PROMPTS_DIR / HEADLINE_FRAMEWORK).read_text(encoding="utf-8")


def test_framework_file_exists(framework_text: str) -> None:
    assert len(framework_text) > 20_000, "the framework is a ~44KB document; this looks truncated"


def test_framework_digits_survived_conversion(framework_text: str) -> None:
    """The signature of the bad conversion: U+00FD where every digit should be."""
    assert "ý" not in framework_text, (
        "U+00FD present — this file was re-converted with a tool that ignores the PDF's "
        "/ToUnicode CMaps. Every digit is corrupt. Re-run the ToUnicode-aware conversion."
    )
    assert sum(c.isdigit() for c in framework_text) > 500


@pytest.mark.parametrize("limit", EXPECTED_LIMITS)
def test_framework_states_its_channel_limits(framework_text: str, limit: str) -> None:
    """Rule 4 of the Value Ladder prompt is unfollowable without these."""
    assert limit in framework_text


def test_framework_carries_the_sections_the_rules_cite(framework_text: str) -> None:
    for section in ("PRE-PUBLICATION CHECKLIST", "HEADLINE FORMULAS BY TRAFFIC TYPE"):
        assert section in framework_text, f"the prompts name {section!r} as the source of record"


def test_validate_rejects_tounicode_blind_conversion() -> None:
    corrupt = "Google Search Ads: ýý characters per headline (ý headlines per ad)"
    with pytest.raises(CorruptReferenceDocError, match="ToUnicode"):
        _validate_reference_doc("fake.md", corrupt)


def test_validate_accepts_the_real_document(framework_text: str) -> None:
    _validate_reference_doc(HEADLINE_FRAMEWORK, framework_text)


# --------------------------------------------------------------------------- injection


def test_library_reaches_every_stage_it_is_registered_for() -> None:
    for asset_id in REFERENCE_LIBRARY:
        block = _load_reference_library(asset_id)
        assert HEADLINE_FRAMEWORK in block, asset_id
        assert "HOW THIS DOCUMENT BINDS YOUR RESPONSE" in block, asset_id


@pytest.mark.parametrize("asset_id", ["icp", "funnel", "sms_sequence", "plan_of_action"])
def test_stages_without_headlines_get_no_library(asset_id: str) -> None:
    """A stage that emits no headline gets nothing: the framework has no SMS channel, ICP is
    research, Funnel is structure, and Plan of Action names tasks rather than marketing copy."""
    assert asset_id in STAGE_CONFIGS
    assert _load_reference_library(asset_id) == ""


def test_registered_stages_are_real_stages() -> None:
    """A typo here would silently inject nothing rather than fail."""
    unknown = set(REFERENCE_LIBRARY) - set(STAGE_CONFIGS)
    assert not unknown, f"REFERENCE_LIBRARY names stages that do not exist: {unknown}"


def test_library_precedes_inputs_which_precede_the_master_prompt() -> None:
    prompt = build_prompt("offers", {"client_name": "Acme"})
    lib = prompt.index("— REFERENCE LIBRARY —")
    inputs = prompt.index("— INPUTS (fill in before submitting) —")
    body = prompt.index("## ROLE")
    assert lib < inputs < body, "the master prompt's closing instruction must stay last"


def test_offers_prompt_no_longer_cites_a_file_it_is_not_given() -> None:
    """The prompt used to point at `...FRAMEWORK.md.pdf`, which was never injected.

    Scoped to the authored prompt, not the whole string: the injected document carries a provenance
    comment naming the PDF it was converted from, which is a record of where it came from rather
    than an instruction to go and read it.
    """
    prompt = build_prompt("offers", {"client_name": "Acme"})
    authored = prompt.split("— END OF REFERENCE LIBRARY —", 1)[1]
    assert ".md.pdf" not in authored
    assert f"assets/Prompts/{HEADLINE_FRAMEWORK}" in authored


def test_phase2_stages_inherit_the_library() -> None:
    """Phase 2's Blog and Lead Magnet need the framework as much as Phase 1's, and the library is
    keyed by asset_id precisely so no second table has to be kept in step."""
    shared = set(REFERENCE_LIBRARY) & set(PHASE2_STAGE_CONFIGS)
    assert shared, "expected Phase 2 to run at least one title/topic stage"
    for asset_id in shared:
        prompt = build_prompt(asset_id, {}, phase="phase2")
        assert HEADLINE_FRAMEWORK in prompt, asset_id
