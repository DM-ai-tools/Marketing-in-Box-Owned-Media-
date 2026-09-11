"""The CRO stage's build-from-scratch mode, and the sentinels the UI writes to reach it.

The case this covers
--------------------
A run's ICP is for "Social Media Marketing for e-commerce" and the client has never had a page for
that service. The CRO stage audits an *existing* page, and both of its page fields are `required` —
so with nothing offered, the page nominated is whichever one exists, usually the home page. That is
wrong twice over: the audit is then about a page the run is not for, and `_design_source_url` reads
the same answer, so the home page also becomes the design reference for every page the run builds.

The master prompt already has the right answer to this:

    Default execution mode is **Quick Win (Spear Gun)** … If the inputs state "NEW PAGE", switch to
    build-from-scratch mode and skip Step 2's before/after comparisons, retaining every other
    instruction.

and both fields' own instructions offer the sentinel. So the mode was reachable all along by typing
one exact phrase, and unreachable in practice. `NEW_PAGE_OPTIONS` in the frontend's `pipelineData.ts`
now writes those two answers from a button.

That makes three separate files that have to agree — the prompt, the schema, and the frontend
table — with nothing but this file connecting them. Any one of them drifting produces the same
failure: a button that claims to switch modes, an answer that reads as ordinary page copy, and a
"rewrite" of a page that does not exist.

No network and no model call: the prompt is read off disk.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app.services.generation import _SCHEMAS_DIR, build_prompt

#: The phrase the prompt branches on. Deliberately short — the prompt tests for it as a substring,
#: so the two full sentinels only have to contain it.
MARKER = "NEW PAGE"

CRO_PROMPT = Path(__file__).resolve().parents[1] / "assets" / "Prompts" / "Master_Prompt_Universal_Page_Rewrite_v1.md"
PIPELINE_DATA = (
    Path(__file__).resolve().parents[2] / "frontend" / "src" / "pipeline" / "pipelineData.ts"
)

URL_FIELD = "existing_page_url"
CONTENT_FIELD = "existing_page_content"


def _cro_fields() -> dict[str, dict]:
    data = json.loads((_SCHEMAS_DIR / "cro.json").read_text(encoding="utf-8"))
    return {f["field_id"]: f for f in data["fields"]}


def _inputs_block(prompt: str) -> str:
    head, _, _ = prompt.partition("— END OF INPUTS —")
    return head


# --------------------------------------------------------------------------------------
# The prompt
# --------------------------------------------------------------------------------------


def test_the_prompt_still_has_a_build_from_scratch_mode() -> None:
    """The load-bearing one. Every button and sentinel below is worthless if this clause is edited
    out, and nothing else in the codebase would notice."""
    text = CRO_PROMPT.read_text(encoding="utf-8")
    assert MARKER in text
    clause = re.search(r"If the inputs state \"NEW PAGE\"[^.]*\.", text, re.S)
    assert clause is not None, "the build-from-scratch clause is gone from the CRO prompt"
    assert "build-from-scratch" in clause.group(0)


def test_the_mode_is_a_switch_the_prompt_resolves_and_reports() -> None:
    """Step 0 states the resolved mode before anything else, which is what makes the mode visible in
    the output rather than something the operator has to infer from a missing section."""
    text = CRO_PROMPT.read_text(encoding="utf-8")
    assert "MODE RESOLUTION" in text


# --------------------------------------------------------------------------------------
# The schema
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("field_id", [URL_FIELD, CONTENT_FIELD])
def test_both_page_fields_offer_the_sentinel_in_their_own_instructions(field_id: str) -> None:
    field = _cro_fields()[field_id]
    assert MARKER in field["raw_explanation"], field["raw_explanation"]


@pytest.mark.parametrize("field_id", [URL_FIELD, CONTENT_FIELD])
def test_both_page_fields_are_still_required(field_id: str) -> None:
    """Which is why the offer has to exist. A `required` field with no valid answer for a real
    situation is a dead end, and the dead end was reached by nominating the wrong page."""
    assert _cro_fields()[field_id]["required"] is True


def test_the_content_field_is_read_from_the_url_field() -> None:
    """`SCRAPE_SOURCES` pairs them, so answering the URL normally fills the content by reading the
    page. That pairing is why the two sentinels are written together: with no page to read, the
    content question is the same question again."""
    text = PIPELINE_DATA.read_text(encoding="utf-8")
    assert re.search(rf"{CONTENT_FIELD}:\s*\"{URL_FIELD}\"", text)


# --------------------------------------------------------------------------------------
# The frontend table — the drift test
# --------------------------------------------------------------------------------------


def _new_page_option() -> dict[str, str]:
    if not PIPELINE_DATA.exists():  # pragma: no cover - monorepo checkout always has it
        pytest.skip(f"frontend pipelineData not present at {PIPELINE_DATA}")
    text = PIPELINE_DATA.read_text(encoding="utf-8")
    block = re.search(r"NEW_PAGE_OPTIONS[^=]*=\s*\{(.*?)\n\};", text, re.S)
    assert block is not None, "NEW_PAGE_OPTIONS is gone from pipelineData.ts"
    cro = re.search(r"cro:\s*\{(.*?)\n  \},", block.group(1), re.S)
    assert cro is not None, "NEW_PAGE_OPTIONS has no entry for cro"
    return dict(re.findall(r'(\w+):\s*"([^"]*)"', cro.group(1)))


def test_the_ui_writes_the_fields_the_schema_actually_has() -> None:
    option = _new_page_option()
    fields = _cro_fields()
    assert option["urlFieldId"] == URL_FIELD
    assert option["contentFieldId"] == CONTENT_FIELD
    assert option["urlFieldId"] in fields
    assert option["contentFieldId"] in fields
    # The subject is read off an answer given earlier in the same intake, so it has to be a field of
    # this asset and it has to come first.
    assert option["subjectFieldId"] in fields
    order = list(fields)
    assert order.index(option["subjectFieldId"]) < order.index(option["urlFieldId"])


def test_the_ui_writes_answers_the_prompt_will_switch_on() -> None:
    option = _new_page_option()
    assert MARKER in option["urlAnswer"]
    assert MARKER in option["contentAnswer"]


@pytest.mark.parametrize("pair", [("urlAnswer", URL_FIELD), ("contentAnswer", CONTENT_FIELD)])
def test_each_answer_is_the_fields_own_instruction_verbatim(pair: tuple[str, str]) -> None:
    """Not merely containing "NEW PAGE": the answer lands in the INPUTS block, which an operator
    reads back, so it should be the wording the field itself offers rather than a paraphrase. This
    is also the check that would catch an em dash quietly turned into a hyphen by an editor."""
    key, field_id = pair
    answer = _new_page_option()[key]
    instruction = _cro_fields()[field_id]["raw_explanation"]
    assert answer in instruction, f"{answer!r} is not offered by {field_id}: {instruction!r}"


def test_the_stage_offered_instead_is_a_real_asset() -> None:
    from app.services.generation import STAGE_CONFIGS

    assert _new_page_option()["insteadAssetId"] in STAGE_CONFIGS


# --------------------------------------------------------------------------------------
# End to end: the answers reach the prompt
# --------------------------------------------------------------------------------------


def test_the_sentinels_reach_the_inputs_block() -> None:
    """The whole chain in one assertion: the button's answers, through `build_prompt`, into the block
    the model reads its mode from.

    Asserted as whole lines rather than as substrings. An unanswered field renders
    `Label: (not specified)` — it does *not* echo its own instruction — so a substring match would
    also have passed on a `build_prompt` that dropped the answers entirely.
    """
    option = _new_page_option()
    answers = {URL_FIELD: option["urlAnswer"], CONTENT_FIELD: option["contentAnswer"]}
    lines = _inputs_block(build_prompt("cro", answers)).splitlines()
    assert f"Existing Page URL: {option['urlAnswer']}" in lines
    assert f"Existing Page Content: {option['contentAnswer']}" in lines


def test_an_ordinary_url_does_not_trip_the_mode() -> None:
    """The other half of it: nothing in an ordinary run's INPUTS block may contain the marker, or
    every run would silently build from scratch."""
    answers = {URL_FIELD: "https://example.com/social-media-marketing", CONTENT_FIELD: "Real page copy."}
    block = _inputs_block(build_prompt("cro", answers))
    assert "Existing Page URL: https://example.com/social-media-marketing" in block.splitlines()
    assert MARKER not in block, "an ordinary answer left the NEW PAGE marker in the INPUTS block"
# --------------------------------------------------------------------------------------
# What the sentinel must NOT become
# --------------------------------------------------------------------------------------


def test_the_sentinel_is_not_read_as_a_design_source() -> None:
    """`existing_page_url` is the first entry in `_DESIGN_SOURCE_FIELDS`, so whatever is in it also
    decides which page DESIGN.md is captured from. The sentinel has to fall *through* that list, not
    sit at the top of it as an unusable value — and it must not be mistaken for a bare domain by
    `_as_url`, which would send a 17-credit capture at nothing."""
    from app.routers.pipeline import _as_url, _design_source_url

    option = _new_page_option()
    assert _as_url(option["urlAnswer"]) is None
    assert _as_url(option["contentAnswer"]) is None

    answers = {
        URL_FIELD: option["urlAnswer"],
        "reference_design_source": "https://client.example/social-media-marketing",
    }
    assert _design_source_url(answers, {}) == "https://client.example/social-media-marketing"


def test_with_no_page_and_no_reference_the_design_source_is_the_client_site() -> None:
    """The remaining fallback, stated so it is a decision rather than an accident: with no page and
    no nominated reference there is nothing else to read a palette from, and the run says so in
    DESIGN.md rather than inventing one."""
    from app.routers.pipeline import _design_source_url

    option = _new_page_option()
    answers = {URL_FIELD: option["urlAnswer"], "client_website_url": "client.example"}
    assert _design_source_url(answers, {}) == "https://client.example"
