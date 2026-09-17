"""The CRO stage's client-level settings — captured once, inherited by every later run.

`app/services/cro_settings.py` exists so a Phase 2 run for a sub-service does not have to re-ask how
the client sells. That makes it a *drift* problem more than a logic problem: the module composes a
document, a TypeScript table decides which fields read it, and a second TypeScript table knows how to
find one entry inside it. All three are edited by hand, none imports the others, and when they
disagree nothing breaks loudly — the extractor simply finds nothing, the field falls back to
`ask_user_if_missing`, and Phase 2 quietly goes back to asking the twenty questions this was built to
remove. There is no error, no log line, and no failing request; the only symptom is an operator
answering something they already answered months ago.

So most of what is here parses the other two files and proves they still agree, in the same spirit as
`test_dependencies.py`'s catalog drift tests and `test_new_page_mode.py`'s three-file check.

No database and no network: the route test fakes the session at the same seams
`test_standalone_runs.py` does.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers import pipeline as pipeline_router
from app.services import cro_settings
from app.services.dependencies import WRITES

_FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "src"
_PHASE2_CATALOG = _FRONTEND / "data" / "phase2Catalog.ts"
_SUB_KEYS = _FRONTEND / "lib" / "contextSubKeys.ts"
_CRO_SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "drafts" / "cro.json"

RUN_ID = "11111111-1111-1111-1111-111111111111"


# --------------------------------------------------------------------------------------
# What is captured
# --------------------------------------------------------------------------------------


def test_every_captured_field_is_a_real_cro_input() -> None:
    """A field id that is not on the stage is captured from an answer that never arrives, so the
    document is short one setting and the Phase 2 question comes back."""
    schema_ids = {f["field_id"] for f in json.loads(_CRO_SCHEMA.read_text(encoding="utf-8"))["fields"]}
    missing = [f for f in cro_settings.CLIENT_SETTING_FIELD_IDS if f not in schema_ids]
    assert not missing, f"captured fields that cro.json does not have: {missing}"


def test_labels_come_from_the_schema() -> None:
    """Rendered under a label the operator never saw, a setting reads as a different question."""
    labels = {f["field_id"]: f["label"] for f in json.loads(_CRO_SCHEMA.read_text(encoding="utf-8"))["fields"]}
    assert dict(cro_settings.settings_fields()) == {
        field_id: labels[field_id] for field_id in cro_settings.CLIENT_SETTING_FIELD_IDS
    }


def test_page_specific_answers_are_not_captured() -> None:
    """The line this module draws. Each of these describes one page or one run, and carrying it to
    another service's page would be worse than asking: a locked heading pinned onto a page that has
    no such section, or the previous page's URL presented as this one's."""
    for field_id in (
        "existing_page_url",
        "existing_page_content",
        "page_scope",
        "target_service_or_sub_service",
        "parent_pillar_page_url",
        "sibling_pages_not_to_cannibalise",
        "existing_ranking_keywords_or_gsc_queries",
        "locked_offer_service_product_names",
        "locked_section_names_or_headings",
        "locked_content_blocks",
        "locked_legal_compliance_text",
        "cro_framework",
        "additional_notes_constraints",
        # Already run-level facts; a second home for them would be a second thing to keep in step.
        "client_name",
        "client_website_url",
    ):
        assert field_id not in cro_settings.CLIENT_SETTING_FIELD_IDS, field_id


def test_capture_keeps_only_the_client_level_answers() -> None:
    captured = cro_settings.capture(
        {
            "buyer_type": "B2B",
            "existing_page_url": "https://example.com/old",
            "client_name": "Acme",
            "word_for_the_reader": "marketing manager",
        }
    )
    assert captured is not None
    assert captured["fields"] == {"buyer_type": "B2B", "word_for_the_reader": "marketing manager"}


def test_capture_drops_blank_answers() -> None:
    """A field the operator skipped is absent, not present-and-empty. Stored empty it would still
    resolve on the Phase 2 side and fill the field with nothing, where absent falls back to asking."""
    captured = cro_settings.capture({"buyer_type": "B2B", "sales_motion": "   ", "geo_mode": ""})
    assert captured is not None
    assert captured["fields"] == {"buyer_type": "B2B"}


def test_capture_is_none_when_there_is_nothing_client_level() -> None:
    """None rather than an empty document: `_latest_context_entry` takes the highest version, not the
    fullest, so an empty row written by a stage approved from a pasted draft would shadow the real
    one a later re-run produces."""
    assert cro_settings.capture({}) is None
    assert cro_settings.capture({"client_name": "Acme", "existing_page_url": "https://x/"}) is None


def test_one_setting_is_one_line() -> None:
    """The extractor reads line by line, so a pasted multi-line answer has to arrive flattened or it
    swallows every setting rendered after it."""
    captured = cro_settings.capture({"pricing_facts": "From $2,500/mo\n\nExcludes ad spend.", "buyer_type": "B2B"})
    assert captured is not None
    assert captured["fields"]["pricing_facts"] == "From $2,500/mo Excludes ad spend."
    body = [line for line in str(captured["content"]).splitlines() if line.startswith("- ")]
    assert len(body) == 2


def test_the_key_is_declared_as_a_cro_output() -> None:
    """Readers resolve it down `source_run_id` like any other document, which only works if the
    producing asset declares it. `test_dependencies.py` proves the frontend catalog agrees."""
    assert cro_settings.CONTEXT_KEY in WRITES[cro_settings.PRODUCER_ASSET_ID]


# --------------------------------------------------------------------------------------
# The document the extractor has to be able to read
# --------------------------------------------------------------------------------------


def _extract(content: str, sub_key: str) -> str | None:
    """A Python mirror of `valueForLabel` in `lib/contextSubKeys.ts`, bolded pass only.

    Duplicated deliberately, and it is the *duplication* that is the test: this file cannot import
    the TypeScript, so the next best thing is to state the contract the renderer has to satisfy and
    fail here the moment the rendered shape stops satisfying it. `smoke/phase2cro.tsx` runs the real
    extractor over the same shape from the other side.
    """
    pattern = rf"(?:^|[|.·•;\-\s])\s*{re.escape(sub_key)}\s*[=:]\s*\*\*([^*|\n]+)\*\*"
    found = re.search(pattern, content, re.IGNORECASE)
    return found.group(1).strip() if found else None


def test_every_captured_setting_can_be_read_back_out() -> None:
    answers = {field_id: f"value-for-{field_id}" for field_id in cro_settings.CLIENT_SETTING_FIELD_IDS}
    captured = cro_settings.capture(answers)
    assert captured is not None
    content = str(captured["content"])

    for field_id in cro_settings.CLIENT_SETTING_FIELD_IDS:
        assert _extract(content, field_id) == f"value-for-{field_id}", field_id


def test_a_setting_not_answered_is_not_readable() -> None:
    """Undefined is the right answer for an unanswered setting — it is what sends the field back to
    being asked, rather than filling it with a neighbouring value."""
    captured = cro_settings.capture({"buyer_type": "B2B"})
    assert captured is not None
    assert _extract(str(captured["content"]), "sales_motion") is None


def test_values_with_punctuation_survive() -> None:
    """The real answers are not single words. A claim tier carries a digit and a hyphen, a conversion
    goal is a sentence with a comma in it, and both have to come back whole."""
    captured = cro_settings.capture(
        {
            "claim_substantiation_tier": "2 PROFESSIONALLY REGULATED",
            "primary_conversion_goal": "Book a free 30-minute strategy call, routed to the contact form",
        }
    )
    assert captured is not None
    content = str(captured["content"])
    assert _extract(content, "claim_substantiation_tier") == "2 PROFESSIONALLY REGULATED"
    assert _extract(content, "primary_conversion_goal") == (
        "Book a free 30-minute strategy call, routed to the contact form"
    )


# --------------------------------------------------------------------------------------
# Drift against the two TypeScript tables
# --------------------------------------------------------------------------------------


def _ts_string_list(text: str, const_name: str) -> list[str]:
    found = re.search(rf"const {const_name} = \[(.*?)\] as const;", text, re.DOTALL)
    assert found is not None, f"{const_name} not found or no longer a plain `as const` array"
    return re.findall(r'"([a-z_0-9]+)"', found.group(1))


def test_the_frontend_reads_exactly_what_is_captured() -> None:
    """`CRO_CLIENT_SETTINGS` in `data/phase2Catalog.ts` is the list of Phase 2 CRO fields rewired to
    read this document. A field captured but not listed is a question still being asked for no
    reason; a field listed but not captured is a field that silently falls back to asking."""
    listed = _ts_string_list(_PHASE2_CATALOG.read_text(encoding="utf-8"), "CRO_CLIENT_SETTINGS")
    assert listed == list(cro_settings.CLIENT_SETTING_FIELD_IDS)


def test_the_extractor_knows_every_captured_setting() -> None:
    """`cro_client_settings` in `lib/contextSubKeys.ts` maps each sub-key to the spellings it is
    written under. A captured setting missing from it is unreadable however well it was stored."""
    text = _SUB_KEYS.read_text(encoding="utf-8")
    block = re.search(r"cro_client_settings:\s*\{(.*?)\n  \},", text, re.DOTALL)
    assert block is not None, "cro_client_settings is no longer a block of lib/contextSubKeys.ts"

    registered = set(re.findall(r"^\s{4}([a-z_0-9]+):", block.group(1), re.MULTILINE))
    assert registered == set(cro_settings.CLIENT_SETTING_FIELD_IDS)

    # The field_id itself must be one of the spellings: it is the one the server actually renders,
    # and the only one that is an exact match rather than a guess at the model's prose.
    for field_id in cro_settings.CLIENT_SETTING_FIELD_IDS:
        entry = re.search(rf"^\s{{4}}{field_id}:\s*(\[[^\]]*\]|\[[^\]]*$)", block.group(1), re.MULTILINE | re.DOTALL)
        assert entry is not None, field_id
        assert f'"{field_id}"' in entry.group(1), f"{field_id} is not matched by its own id"


def test_the_frontend_key_matches() -> None:
    text = _PHASE2_CATALOG.read_text(encoding="utf-8")
    found = re.search(r'CRO_CLIENT_SETTINGS_KEY = "([a-z_]+)"', text)
    assert found is not None
    assert found.group(1) == cro_settings.CONTEXT_KEY


# --------------------------------------------------------------------------------------
# The save route
# --------------------------------------------------------------------------------------


@dataclass
class _FakeRun:
    current_stage_id: str | None = None
    source_run_id: Any = None


@dataclass
class _FakeResult:
    def scalar_one_or_none(self) -> Any:
        return None


@dataclass
class _FakeSession:
    """Only what `save_stage` touches: two `get`s, one `execute`, then `add`/`commit`."""

    added: list[Any] = field(default_factory=list)
    committed: bool = False

    async def get(self, _model: Any, _ident: Any) -> Any:
        return _FakeRun()

    async def execute(self, _stmt: Any) -> _FakeResult:
        return _FakeResult()

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.committed = True

    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, *_exc: Any) -> bool:
        return False


@pytest.fixture(name="session")
def _session(monkeypatch: pytest.MonkeyPatch) -> _FakeSession:
    session = _FakeSession()
    monkeypatch.setattr(pipeline_router, "get_sessionmaker", lambda: (lambda: session))

    async def fake_next_version(_session: Any, _run: uuid.UUID, _context_key: str) -> int:
        return 1

    monkeypatch.setattr(pipeline_router, "_next_version", fake_next_version)
    return session


@pytest.fixture(name="client")
def _client() -> TestClient:
    return TestClient(app)


def _save(client: TestClient, asset_id: str, body: dict[str, Any]) -> Any:
    response = client.post(f"/pipeline/runs/{RUN_ID}/stages/{asset_id}/save", json=body)
    assert response.status_code == 200, response.text
    return response


def _context_rows(session: _FakeSession) -> dict[str, Any]:
    return {row.context_key: row for row in session.added if hasattr(row, "context_key")}


def test_saving_cro_with_answers_publishes_the_settings(session: _FakeSession, client: TestClient) -> None:
    _save(
        client,
        "cro",
        {
            "content": "# The rewrite",
            "answers": {"buyer_type": "B2B", "sales_motion": "CONSULT-LED", "existing_page_url": "https://x/"},
        },
    )

    rows = _context_rows(session)
    assert "cro" in rows, "the stage's own document must still be saved"
    settings = rows.get(cro_settings.CONTEXT_KEY)
    assert settings is not None, "approving CRO with answers must publish the client settings"
    assert settings.value["fields"] == {"buyer_type": "B2B", "sales_motion": "CONSULT-LED"}
    assert settings.written_by_asset_id == "cro"


def test_saving_cro_without_answers_publishes_nothing_extra(session: _FakeSession, client: TestClient) -> None:
    """A stage approved from a draft the operator pasted in has no intake behind it. Writing an empty
    settings row for it would shadow whatever a real run had already stored."""
    _save(client, "cro", {"content": "# The rewrite"})
    assert cro_settings.CONTEXT_KEY not in _context_rows(session)


def test_saving_another_stage_publishes_nothing_extra(session: _FakeSession, client: TestClient) -> None:
    _save(client, "pillar_page", {"content": "<html></html>", "answers": {"buyer_type": "B2B"}})
    assert cro_settings.CONTEXT_KEY not in _context_rows(session)


def test_the_settings_row_is_versioned_on_its_own_key(session: _FakeSession, client: TestClient) -> None:
    """Its own key, not folded into the stage document, so re-approving a corrected CRO stage
    supersedes the settings with it and a reader gets the newest either way."""
    _save(client, "cro", {"content": "# The rewrite", "answers": {"buyer_type": "B2B"}})
    settings = _context_rows(session)[cro_settings.CONTEXT_KEY]
    assert settings.context_key == cro_settings.CONTEXT_KEY
    assert settings.version == 1
