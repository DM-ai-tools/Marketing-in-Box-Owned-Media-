"""Tests for the two routes that make a standalone run possible.

  - `GET  /pipeline/runs/{id}/readiness/{asset}` — what a stage still needs on this run
  - `POST /pipeline/runs/{id}/context`           — hand a document over instead of running for it

Both talk to Postgres, which the rest of this suite does not have. So the session is faked at the
two seams the routes actually use — `_latest_context_entry` and `_next_version`, both module-level
functions — and what is tested is the routes' own reasoning, which is where every wrong answer an
operator would act on lives:

  - a document approved as a *stage* satisfies a field that asks for one of the stage's other
    context keys. This is the one that matters most: `save_stage` files output under `asset_id` and
    nothing else, so probing `cro_rewritten_copy` alone finds nothing on a run whose CRO stage was
    approved, and the route would send the operator to re-run a stage they had already run,
  - a competitor prepass is never something to run first or to supply,
  - `unresolved_context_key` is a question, not a missing document, so it cannot make a stage
    permanently blocked,
  - and "run these first" shrinks as the run fills up.

The database's own behaviour (append-only enforcement, the version sequence) is the schema's
business and is not re-tested here.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers import pipeline as pipeline_router

RUN_ID = "11111111-1111-1111-1111-111111111111"
PARENT_RUN_ID = "22222222-2222-2222-2222-222222222222"


@dataclass
class _FakeEntry:
    value: dict[str, Any]
    version: int = 1


@dataclass
class _FakeSession:
    """Only what the two routes touch: one `get` for the run, plus `add`/`commit` for the seed."""

    run_exists: bool = True
    added: list[Any] = field(default_factory=list)
    committed: bool = False

    async def get(self, _model: Any, _ident: Any) -> Any:
        return object() if self.run_exists else None

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.committed = True

    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, *_exc: Any) -> bool:
        return False


@dataclass
class _Store:
    """What the run holds, keyed exactly as `context_entries` keys it.

    `on_parent` is the inherited half — a Phase 2 run reading its Phase 1 parent, which
    `_latest_context_entry` walks to and which readiness must report as ready rather than missing.
    """

    on_run: dict[str, _FakeEntry] = field(default_factory=dict)
    on_parent: dict[str, _FakeEntry] = field(default_factory=dict)


@pytest.fixture(name="store")
def _store(monkeypatch: pytest.MonkeyPatch) -> _Store:
    store = _Store()
    session = _FakeSession()

    monkeypatch.setattr(pipeline_router, "get_sessionmaker", lambda: (lambda: session))

    async def fake_latest(_session: Any, run_uuid: uuid.UUID, context_key: str) -> Any:
        entry = store.on_run.get(context_key)
        if entry is not None:
            return entry, run_uuid
        entry = store.on_parent.get(context_key)
        if entry is not None:
            return entry, uuid.UUID(PARENT_RUN_ID)
        return None

    monkeypatch.setattr(pipeline_router, "_latest_context_entry", fake_latest)

    async def fake_next_version(_session: Any, _run: uuid.UUID, context_key: str) -> int:
        existing = store.on_run.get(context_key)
        return (existing.version if existing else 0) + 1

    monkeypatch.setattr(pipeline_router, "_next_version", fake_next_version)
    return store


@pytest.fixture(name="client")
def _client() -> TestClient:
    return TestClient(app)


def _readiness(client: TestClient, asset_id: str, phase: str | None = None) -> dict[str, Any]:
    params = {"phase": phase} if phase else None
    response = client.get(f"/pipeline/runs/{RUN_ID}/readiness/{asset_id}", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def _by_key(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {d["context_key"]: d for d in payload["dependencies"]}


def _doc(text: str = "A real document, long enough to be one.", **extra: Any) -> _FakeEntry:
    return _FakeEntry(value={"content": text, **extra})


# --------------------------------------------------------------------------------------
# An empty run
# --------------------------------------------------------------------------------------


def test_an_empty_run_blocks_offers_on_the_icp_alone(client: TestClient, store: _Store) -> None:
    payload = _readiness(client, "offers")
    assert payload["blocked"] is True
    assert payload["run_first"] == ["icp"]
    icp = _by_key(payload)["icp"]
    assert icp["ready"] is False
    assert icp["required"] is True
    assert icp["producer"] == "icp"
    assert icp["stored_under"] is None


def test_icp_is_ready_to_run_on_an_empty_run(client: TestClient, store: _Store) -> None:
    payload = _readiness(client, "icp")
    assert payload["blocked"] is False
    assert payload["run_first"] == []
    assert payload["dependencies"] == []
    assert payload["writes"] == ["icp"]


def test_the_social_audit_is_never_blocked(client: TestClient, store: _Store) -> None:
    """Its only inputs are its own competitor scan and questions, so it is the one stage an
    operator can always start at."""
    payload = _readiness(client, "social_content_strategy_audit")
    assert payload["blocked"] is False
    assert payload["run_first"] == []


# --------------------------------------------------------------------------------------
# The two-key resolution
# --------------------------------------------------------------------------------------


def test_an_approved_stage_satisfies_a_field_asking_for_one_of_its_other_keys(
    client: TestClient, store: _Store
) -> None:
    """`offers` asks for `cro_rewritten_copy`. `save_stage` files the CRO stage under `cro`. If this
    is not resolved, readiness tells an operator to re-run a stage they have already approved."""
    store.on_run["icp"] = _doc()
    store.on_run["cro"] = _doc("The rewritten page copy.")

    payload = _readiness(client, "offers")
    rewrite = _by_key(payload)["cro_rewritten_copy"]
    assert rewrite["ready"] is True
    assert rewrite["stored_under"] == "cro"
    assert rewrite["source"] == "this_run"
    assert rewrite["chars"] == len("The rewritten page copy.")
    assert payload["blocked"] is False
    assert payload["run_first"] == []


def test_a_seeded_document_is_found_under_the_context_key_itself(
    client: TestClient, store: _Store
) -> None:
    store.on_run["cro_rewritten_copy"] = _FakeEntry(value={"content": "Pasted copy.", "seeded": True})
    rewrite = _by_key(_readiness(client, "offers"))["cro_rewritten_copy"]
    assert rewrite["ready"] is True
    assert rewrite["seeded"] is True
    assert rewrite["stored_under"] == "cro_rewritten_copy"


def test_the_key_itself_wins_over_the_producing_stage(client: TestClient, store: _Store) -> None:
    """An operator who pasted a better CRO rewrite gets the one they pasted, not the generated one
    the stage happens to also hold."""
    store.on_run["cro"] = _doc("Generated.")
    store.on_run["cro_rewritten_copy"] = _FakeEntry(value={"content": "Mine.", "seeded": True})
    rewrite = _by_key(_readiness(client, "offers"))["cro_rewritten_copy"]
    assert rewrite["stored_under"] == "cro_rewritten_copy"
    assert rewrite["seeded"] is True


def test_a_stage_run_in_the_parent_run_is_ready_and_labelled_inherited(
    client: TestClient, store: _Store
) -> None:
    store.on_parent["icp"] = _doc()
    icp = _by_key(_readiness(client, "offers"))["icp"]
    assert icp["ready"] is True
    assert icp["source"] == "inherited"
    assert icp["from_run_id"] == PARENT_RUN_ID
    assert _readiness(client, "offers")["blocked"] is False


def test_an_entry_with_no_content_is_missing_not_ready(client: TestClient, store: _Store) -> None:
    """The shape a row written before DESIGN.md existed can have. Reported ready, it would hand the
    stage an empty document — `get_run_context` 404s on exactly this condition."""
    store.on_run["icp"] = _FakeEntry(value={"note": "no content here"})
    assert _by_key(_readiness(client, "offers"))["icp"]["ready"] is False
    assert _readiness(client, "offers")["blocked"] is True


def test_a_blank_content_string_is_missing_not_ready(client: TestClient, store: _Store) -> None:
    store.on_run["icp"] = _FakeEntry(value={"content": ""})
    assert _by_key(_readiness(client, "offers"))["icp"]["ready"] is False


# --------------------------------------------------------------------------------------
# run_first shrinks as the run fills up
# --------------------------------------------------------------------------------------


def test_run_first_is_the_whole_chain_on_an_empty_run(client: TestClient, store: _Store) -> None:
    assert _readiness(client, "sms_sequence")["run_first"] == ["icp", "cro", "pillar_page", "funnel"]


def test_run_first_drops_what_the_run_already_has(client: TestClient, store: _Store) -> None:
    """The difference between "run four stages" and "run one" — and the reason this is computed
    against the run rather than read off the static graph."""
    store.on_run["icp"] = _doc()
    store.on_run["cro"] = _doc()
    store.on_run["pillar_page"] = _doc()
    assert _readiness(client, "sms_sequence")["run_first"] == ["funnel"]


def test_a_seeded_document_removes_its_whole_branch_from_run_first(
    client: TestClient, store: _Store
) -> None:
    """Seeding the funnel stages removes not just `funnel` but `pillar_page` and `cro` behind it,
    which were only in the chain to get there."""
    store.on_run["icp"] = _doc()
    store.on_run["cro_rewritten_copy"] = _FakeEntry(value={"content": "Pasted.", "seeded": True})
    store.on_run["funnel_stages"] = _FakeEntry(value={"content": "Pasted stages.", "seeded": True})
    payload = _readiness(client, "sms_sequence")
    assert payload["run_first"] == []
    assert payload["blocked"] is False


def test_run_first_never_names_the_asset_being_started(client: TestClient, store: _Store) -> None:
    for asset_id in ("offers", "blog", "book", "sms_sequence", "plan_of_action"):
        assert asset_id not in _readiness(client, asset_id)["run_first"]


# --------------------------------------------------------------------------------------
# What is not the operator's problem
# --------------------------------------------------------------------------------------


def test_the_competitor_prepass_is_reported_apart_and_never_blocks(
    client: TestClient, store: _Store
) -> None:
    store.on_run["icp"] = _doc()
    store.on_run["cro"] = _doc()
    payload = _readiness(client, "offers")
    assert payload["prepass"] == "competitor_analysis_offers"
    assert [f["field_id"] for f in payload["prepass_fields"]] == ["competitor_analysis"]
    assert payload["prepass_fields"][0]["ready"] is False
    assert "competitor_analysis_offers" not in _by_key(payload)
    assert payload["blocked"] is False
    assert "competitor_analysis_offers" not in payload["seedable"]


def test_a_prepass_already_run_on_this_run_is_reported_ready(
    client: TestClient, store: _Store
) -> None:
    """So the UI can say whether entering the stage spends a search or reuses what is there."""
    store.on_run["competitor_analysis_offers"] = _doc("Five competitors.")
    payload = _readiness(client, "offers")
    assert payload["prepass_fields"][0]["ready"] is True
    assert payload["prepass_fields"][0]["version"] == 1


def test_lead_magnets_required_competitor_list_does_not_block_it(
    client: TestClient, store: _Store
) -> None:
    """It is `required` and nothing upstream writes it, because its own prepass does. Counted as a
    dependency it would make the stage permanently unstartable."""
    store.on_run["icp"] = _doc()
    store.on_run["cro"] = _doc()
    store.on_run["pillar_page"] = _doc()
    payload = _readiness(client, "lead_magnet")
    assert payload["blocked"] is False
    assert [f["field_id"] for f in payload["prepass_fields"]] == ["competitor_lead_magnet_list"]


def test_an_always_asked_field_is_flagged_manual_and_does_not_block(
    client: TestClient, store: _Store
) -> None:
    """`funnel_hub_media`'s reference folder is `required` with no upstream key at all. It is a
    question the stage asks every time; treated as a missing document it would report that stage as
    permanently blocked with nothing the operator could do about it."""
    store.on_run["icp"] = _doc()
    store.on_run["cro"] = _doc()
    store.on_run["pillar_page"] = _doc()
    store.on_run["funnel"] = _doc()
    payload = _readiness(client, "funnel_hub_media")
    manual = [d for d in payload["dependencies"] if d["manual"]]
    assert [d["field_id"] for d in manual] == ["reference_folder_knowledge_base"]
    assert manual[0]["required"] is True
    assert manual[0]["ready"] is False
    assert payload["blocked"] is False
    assert "unresolved_context_key" not in payload["seedable"]


def test_an_optional_missing_dependency_does_not_block(client: TestClient, store: _Store) -> None:
    store.on_run["icp"] = _doc()
    payload = _readiness(client, "offers")
    assert any(not d["required"] and not d["ready"] for d in payload["dependencies"])
    assert payload["blocked"] is False


# --------------------------------------------------------------------------------------
# The seedable list is the "I'll provide it" offer
# --------------------------------------------------------------------------------------


def test_seedable_lists_only_this_stages_own_keys(client: TestClient, store: _Store) -> None:
    payload = _readiness(client, "offers")
    assert set(payload["seedable"]) == {
        d["context_key"] for d in payload["dependencies"] if d["context_key"] != "unresolved_context_key"
    }
    assert "webinar_script" not in payload["seedable"]


def test_a_key_with_no_producer_is_still_offered_for_seeding(
    client: TestClient, store: _Store
) -> None:
    """`email_sequence_copy` is the case where "run the producer first" is not an option at all —
    nothing writes it — so seeding has to be."""
    payload = _readiness(client, "sms_sequence")
    assert _by_key(payload)["email_sequence_copy"]["producer"] is None
    assert "email_sequence_copy" in payload["seedable"]


def test_readiness_404s_on_a_run_that_does_not_exist(
    client: TestClient, store: _Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        pipeline_router, "get_sessionmaker", lambda: (lambda: _FakeSession(run_exists=False))
    )
    response = client.get(f"/pipeline/runs/{RUN_ID}/readiness/offers")
    assert response.status_code == 404


# --------------------------------------------------------------------------------------
# Seeding
# --------------------------------------------------------------------------------------


def test_seeding_writes_an_append_only_entry_marked_as_seeded(
    client: TestClient, store: _Store
) -> None:
    response = client.post(
        f"/pipeline/runs/{RUN_ID}/context",
        json={"context_key": "icp", "content": "The client's own ICP.", "note": "ICP deck"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body == {
        "run_id": RUN_ID,
        "context_key": "icp",
        "version": 1,
        "chars": len("The client's own ICP."),
        "producer": "icp",
    }

    session = pipeline_router.get_sessionmaker()()
    (entry,) = session.added
    assert entry.context_key == "icp"
    assert entry.value == {"content": "The client's own ICP.", "seeded": True, "note": "ICP deck"}
    # Left null on purpose: claiming the `icp` stage wrote a document it never saw would corrupt the
    # one column that records where output came from.
    assert entry.written_by_asset_id is None
    assert session.committed is True


def test_seeding_a_key_a_stage_publishes_names_the_stage_it_stands_in_for(
    client: TestClient, store: _Store
) -> None:
    response = client.post(
        f"/pipeline/runs/{RUN_ID}/context",
        json={"context_key": "funnel_stages", "content": "Five stages."},
    )
    assert response.status_code == 200
    assert response.json()["producer"] == "funnel"


def test_seeding_appends_a_version_rather_than_replacing(client: TestClient, store: _Store) -> None:
    store.on_run["icp"] = _FakeEntry(value={"content": "First."}, version=3)
    response = client.post(
        f"/pipeline/runs/{RUN_ID}/context", json={"context_key": "icp", "content": "Second."}
    )
    assert response.json()["version"] == 4


def test_seeding_a_key_with_no_producer_reports_none(client: TestClient, store: _Store) -> None:
    response = client.post(
        f"/pipeline/runs/{RUN_ID}/context",
        json={"context_key": "email_sequence_copy", "content": "Six emails."},
    )
    assert response.status_code == 200
    assert response.json()["producer"] is None


def test_seeding_404s_on_a_run_that_does_not_exist(
    client: TestClient, store: _Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        pipeline_router, "get_sessionmaker", lambda: (lambda: _FakeSession(run_exists=False))
    )
    response = client.post(
        f"/pipeline/runs/{RUN_ID}/context", json={"context_key": "icp", "content": "x"}
    )
    assert response.status_code == 404


def test_a_seeded_document_unblocks_the_stage_it_was_seeded_for(
    client: TestClient, store: _Store
) -> None:
    """The whole point, end to end: `offers` is blocked, the operator supplies the ICP, `offers`
    runs. The seed is replayed into the store here because the fake session does not persist."""
    assert _readiness(client, "offers")["blocked"] is True

    response = client.post(
        f"/pipeline/runs/{RUN_ID}/context",
        json={"context_key": "icp", "content": "The client's own ICP."},
    )
    assert response.status_code == 200
    session = pipeline_router.get_sessionmaker()()
    seeded = session.added[-1]
    store.on_run[seeded.context_key] = _FakeEntry(value=seeded.value, version=seeded.version)

    payload = _readiness(client, "offers")
    assert payload["blocked"] is False
    assert payload["run_first"] == []
    assert _by_key(payload)["icp"]["seeded"] is True
