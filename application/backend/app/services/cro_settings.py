"""The client-level half of the CRO stage's intake, kept so a later run does not have to ask again.

The CRO stage collects ~37 inputs and they are not all the same kind of thing. Some describe *this
page* — which URL, which service, what is locked, what the existing copy says — and are worthless to
any other run. The rest describe *the client*: how they sell, who buys, which regulatory tier their
claims sit in, how they are allowed to talk about price, and the words they use for a buyer and for
a first appointment. Those do not change between one service and the next, and asking for them a
second time is asking the operator to re-derive an answer the engagement already settled.

Until this module they were asked a second time, because nothing persisted them. `field_sessions`
has a `resolved_fields` column for exactly this and no code has ever written to it; what actually
crosses from a Phase 1 run into its Phase 2 children is `context_entries`, resolved down
`source_run_id`. So this writes a `ContextEntry` like any other stage output, under
`CONTEXT_KEY`, and a Phase 2 stage reads it through the same inheritance every other document uses.
No new table, no new resolver, no new fallback path.

Why a rendered document rather than only the JSON we already have:

  * `ContextEntry.value` is JSON, so the structured map is stored too (`fields`) and tests read it
    directly. But every existing reader in the UI asks for `content` and gets a string, and
    `lib/contextSubKeys.ts` pulls one entry out of a map-shaped document by regex. Emitting a
    document those already understand means the frontend gains one table entry, not a second way of
    reading context.
  * The one existing map-shaped key, `cro_terminology_map`, is extracted out of an 80KB rewrite the
    model wrote, so the regex is hopeful by necessity. This document we emit ourselves, one setting
    per line in a fixed shape, so the same extractor is exact rather than hopeful.

Long answers (pricing facts, proof assets) are recorded and rendered like everything else, with
their whitespace collapsed so one setting stays one line. The extractor discards anything over its
length limit, so a pasted paragraph degrades to the field being asked — which is right: a pricing
schedule from the headline service is the one thing here that genuinely might not carry over.
"""

from __future__ import annotations

import json
from pathlib import Path

_SCHEMAS_DIR = Path(__file__).resolve().parents[2] / "schemas" / "drafts"

#: The context key the settings document is stored under, and the key a Phase 2 field reads.
CONTEXT_KEY = "cro_client_settings"

#: The stage that writes it. Kept here rather than assumed at the call site so the router's guard
#: and this module's field list cannot come to disagree about which stage is being captured.
PRODUCER_ASSET_ID = "cro"

#: Which of the CRO stage's inputs describe the client rather than the page.
#:
#: Deliberately a list of ids and not of (id, label) pairs: the labels are read from `cro.json`
#: below, so a re-worded field cannot end up rendered under one name here and asked under another.
#:
#: What is *not* here is as considered as what is. `client_name` and `client_website_url` are
#: already run-level facts and need no second home. `page_scope`, `target_service_or_sub_service`,
#: `existing_page_url`, `existing_page_content`, `parent_pillar_page_url`,
#: `sibling_pages_not_to_cannibalise`, `existing_ranking_keywords_or_gsc_queries`, `cro_framework`
#: and `additional_notes_constraints` are about one page or one run. The four `locked_*` fields are
#: the sharpest case: they look client-level and are not — a locked section name is locked on *that
#: page*, and carrying one onto a different service's page would pin a heading the new page has no
#: reason to carry.
CLIENT_SETTING_FIELD_IDS: tuple[str, ...] = (
    "client_industry",
    "sub_vertical_niche",
    "buyer_type",
    "sales_motion",
    "geo_mode",
    "region_location",
    "claim_substantiation_tier",
    "pricing_disclosure_mode",
    "pricing_facts",
    "testimonials_before_after_permitted",
    "word_for_the_reader",
    "word_for_the_thing_being_chosen_between",
    "word_for_the_first_commitment_step",
    "word_for_the_business",
    "words_the_buyer_uses_for_the_outcome",
    "words_to_avoid",
    "tone_of_voice",
    "proof_assets_available",
    "primary_conversion_goal",
    "secondary_conversion_goal",
)


def _labels() -> dict[str, str]:
    """field_id -> the label `cro.json` gives it.

    Read rather than restated so the rendered document and the question an operator answered say the
    same thing. A field id that has disappeared from the schema is left out here and caught by
    `test_cro_settings.py` rather than silently rendering under a stale name.
    """
    data = json.loads((_SCHEMAS_DIR / "cro.json").read_text(encoding="utf-8"))
    return {f["field_id"]: f["label"] for f in data["fields"]}


def settings_fields() -> tuple[tuple[str, str], ...]:
    """The captured fields as (field_id, label), in `CLIENT_SETTING_FIELD_IDS` order."""
    labels = _labels()
    return tuple((field_id, labels[field_id]) for field_id in CLIENT_SETTING_FIELD_IDS if field_id in labels)


def _flatten(value: str) -> str:
    """One setting is one line. A pasted answer keeps its words and loses its line breaks."""
    return " ".join(value.split())


def capture(answers: dict[str, str]) -> dict[str, object] | None:
    """The `ContextEntry.value` for this stage's client-level answers, or None if there are none.

    None rather than an empty document on purpose: a CRO stage saved from a draft the operator
    pasted in by hand carries no intake answers at all, and writing an empty settings row for it
    would shadow the real one a later re-run produces — `_latest_context_entry` takes the highest
    version, not the fullest.

    Both halves are returned because they are read by different things: `content` is what every
    existing context reader and the UI's sub-key extractor see, `fields` is the same data without a
    parse, for anything on this side of the wire.
    """
    captured = {
        field_id: _flatten(str(answers.get(field_id) or ""))
        for field_id, _ in settings_fields()
        if _flatten(str(answers.get(field_id) or ""))
    }
    if not captured:
        return None

    labels = dict(settings_fields())
    lines = [
        f"- {field_id} = **{captured[field_id]}**  ({labels[field_id]})"
        for field_id in CLIENT_SETTING_FIELD_IDS
        if field_id in captured
    ]
    content = (
        "# CRO client settings\n\n"
        "How this client sells, who buys, and the words used for both — resolved once on the CRO\n"
        "stage and reused by later runs for other services. Page-specific answers are deliberately\n"
        "not here.\n\n" + "\n".join(lines) + "\n"
    )
    return {"content": content, "fields": captured}
