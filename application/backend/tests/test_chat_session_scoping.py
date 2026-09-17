"""Chat history is per-account — `app/routers/chat_sessions.py`.

The bug these pin: `chat_sessions` had no owner column and none of the five routes filtered on
anything, so `GET /chat-sessions` returned every row in the table. A brand-new account opened onto
somebody else's client work, and could reopen, overwrite and delete any of it.

Every test here needs Postgres, because the whole claim is about what a SELECT returns — a mocked
session layer would pass while the real query returned the table. The suite skips rather than fails
when no database is reachable, matching `tests/test_auth.py`, whose fixtures this reuses in shape.

Two users per test, as two `TestClient`s. Separate cookie jars is what makes them two browsers, and
"two browsers" is the only faithful model of the thing that broke.
"""

from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient


def _database_reachable() -> bool:
    url = os.environ.get("DATABASE_URL")
    if not url:
        return False
    try:
        import psycopg

        with psycopg.connect(url.replace("postgresql+psycopg://", "postgresql://"), connect_timeout=3):
            return True
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _database_reachable(), reason="No reachable DATABASE_URL; skipping chat-scoping tests."
)

#: Reserved TLD (RFC 2606), so a row left behind by a crashed run can never be mistaken for a real
#: account. Distinct from `test_auth.py`'s domain so the two suites' cleanup cannot collide.
TEST_DOMAIN = "chat-scope-test.invalid"


def _delete_users(*emails: str) -> None:
    """Remove the accounts a test created. `chat_sessions.user_id` is ON DELETE CASCADE, so this
    takes their chats with it — which is itself part of what the column is for."""
    import psycopg

    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(url) as conn:
        for email in emails:
            conn.execute("DELETE FROM users WHERE email = %s", (email,))
        conn.commit()


class Account:
    """One signed-in browser: a `TestClient` with its own cookie jar and its own account."""

    def __init__(self, client: TestClient, email: str) -> None:
        self.client = client
        self.email = email

    def create_chat(self, title: str) -> dict:
        res = self.client.post("/chat-sessions", json={"title": title})
        assert res.status_code == 200, res.text
        return res.json()

    def list_chats(self) -> list[dict]:
        res = self.client.get("/chat-sessions")
        assert res.status_code == 200, res.text
        return res.json()


#: The company name of the one run this suite keeps. Distinctive enough to be recognised in a
#: development database, and to be found again on the next run.
FIXTURE_COMPANY = "ZZZ Chat Scoping Test Client (safe to ignore)"


def _chat_run_id(chat_id: str) -> str | None:
    """The `run_id` foreign key on a chat row. Not exposed by the API — the response carries the
    `state` blob the client sent, which says nothing about whether the column was written."""
    import psycopg

    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(url) as conn:
        row = conn.execute("SELECT run_id FROM chat_sessions WHERE id = %s", (chat_id,)).fetchone()
    return str(row[0]) if row and row[0] else None


def _fixture_run(account: "Account") -> str:
    """A run with approved context, owned by `account` for the length of one test.

    Reused rather than created per test, and never deleted, because it cannot be: `context_entries`
    carries an append-only trigger (`block_mutation`), so `DELETE FROM runs` — which cascades into
    it — is refused by the database. That rule is a real invariant of the context store, not an
    obstacle to work around, so this suite leaves exactly one run behind on first use and finds it
    again afterwards instead of disabling the trigger or accumulating a new run every time.

    Re-attaching it to the current test's chat is always possible: `chat_sessions.run_id` is unique,
    but each test's accounts are deleted afterwards and their chats go with them (ON DELETE
    CASCADE), which releases the claim.

    The run must hold at least one context entry or `list_source_runs` filters it out as having
    nothing to inherit — so the stage save below is load-bearing, not set dressing.
    """
    import psycopg

    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(url) as conn:
        existing = conn.execute(
            "SELECT r.id FROM runs r JOIN clients c ON c.id = r.client_id "
            "WHERE c.company_name = %s AND r.source_run_id IS NULL "
            "AND EXISTS (SELECT 1 FROM context_entries ce WHERE ce.run_id = r.id) LIMIT 1",
            (FIXTURE_COMPANY,),
        ).fetchone()
        if existing is not None:
            # Release any stale claim before handing the run over. `run_id` is unique and
            # `update_chat_session` skips the write rather than 500-ing when it is taken, so a
            # leftover chat pointing here would make the attach below a silent no-op and the test
            # would fail claiming the scoping is broken. An ownerless chat is exactly what gets
            # left behind by a crashed run, since a NULL `user_id` is not reached by the account
            # cleanup's cascade.
            conn.execute(
                "DELETE FROM chat_sessions WHERE run_id = %s AND user_id IS NULL", (existing[0],)
            )
            conn.execute(
                "UPDATE chat_sessions SET run_id = NULL WHERE run_id = %s", (existing[0],)
            )
            conn.commit()
            return str(existing[0])

    created = account.client.post("/pipeline/runs", json={"company_name": FIXTURE_COMPANY})
    assert created.status_code == 200, created.text
    run_id = created.json()["run_id"]

    saved = account.client.post(
        f"/pipeline/runs/{run_id}/stages/icp/save",
        json={"content": "Fixture ICP: independent trades, 5-20 staff."},
    )
    assert saved.status_code == 200, saved.text
    return run_id


@pytest.fixture
def two_users():
    """Two signed-up, signed-in accounts, and their rows removed afterwards.

    Cleanup runs even when the test failed mid-flow, which is why it is in the fixture and goes
    through raw SQL rather than the API.
    """
    from app.main import app

    emails = [f"a-{uuid.uuid4().hex[:10]}@{TEST_DOMAIN}", f"b-{uuid.uuid4().hex[:10]}@{TEST_DOMAIN}"]
    clients: list[TestClient] = []
    accounts: list[Account] = []
    try:
        for email in emails:
            tc = TestClient(app)
            tc.__enter__()
            clients.append(tc)
            res = tc.post(
                "/auth/signup",
                json={"email": email, "password": "correct horse", "full_name": "Test"},
            )
            assert res.status_code in (200, 201), res.text
            accounts.append(Account(tc, email))
        yield accounts[0], accounts[1]
    finally:
        for tc in clients:
            tc.__exit__(None, None, None)
        _delete_users(*emails)


# --------------------------------------------------------------------------------------
# The requirement, stated directly
# --------------------------------------------------------------------------------------


@requires_db
def test_a_new_account_sees_an_empty_history(two_users):
    """The headline requirement: sign up while another account has chats, get nothing.

    Ordered so user A's chats already exist before B's first list call — testing B on an empty
    table would pass against the old unscoped code too.
    """
    alice, bob = two_users
    alice.create_chat("Alice's client")
    alice.create_chat("Alice's second client")

    assert bob.list_chats() == []


@requires_db
def test_each_account_lists_only_its_own_chats(two_users):
    alice, bob = two_users
    alice.create_chat("Alice one")
    alice.create_chat("Alice two")
    bob.create_chat("Bob one")

    assert sorted(c["title"] for c in alice.list_chats()) == ["Alice one", "Alice two"]
    assert [c["title"] for c in bob.list_chats()] == ["Bob one"]


# --------------------------------------------------------------------------------------
# The other four routes. Listing was the visible leak; these were the reachable one — an id
# from a screenshot or a URL was enough.
# --------------------------------------------------------------------------------------


@requires_db
def test_another_users_chat_cannot_be_read(two_users):
    alice, bob = two_users
    chat = alice.create_chat("Alice's confidential client")

    res = bob.client.get(f"/chat-sessions/{chat['id']}")
    assert res.status_code == 404
    # The id must not appear in the body either: the point of 404-over-403 is that the response
    # says nothing about whether the row exists, and echoing it back would undo that.
    assert "confidential" not in res.text


@requires_db
def test_another_users_chat_cannot_be_overwritten(two_users):
    """The autosave route. A PUT that succeeded here would silently replace one operator's
    transcript with another's — destructive, and invisible until they reopened the chat."""
    alice, bob = two_users
    chat = alice.create_chat("Alice's client")

    res = bob.client.put(
        f"/chat-sessions/{chat['id']}",
        json={"title": "Bob was here", "state": {"messages": []}},
    )
    assert res.status_code == 404

    still_alices = alice.client.get(f"/chat-sessions/{chat['id']}").json()
    assert still_alices["title"] == "Alice's client"


@requires_db
def test_another_users_chat_cannot_be_deleted(two_users):
    alice, bob = two_users
    chat = alice.create_chat("Alice's client")

    assert bob.client.delete(f"/chat-sessions/{chat['id']}").status_code == 404
    assert alice.client.get(f"/chat-sessions/{chat['id']}").status_code == 200


@requires_db
def test_a_created_chat_is_owned_by_its_creator_not_by_the_request(two_users):
    """`CreateChatSessionRequest` has no `user_id`, so there is nothing to spoof — this pins that
    adding one later would not silently start working."""
    alice, bob = two_users
    res = bob.client.post(
        "/chat-sessions", json={"title": "Planted", "user_id": str(uuid.uuid4())}
    )
    assert res.status_code == 200

    assert [c["title"] for c in bob.list_chats()] == ["Planted"]
    assert alice.list_chats() == []


# --------------------------------------------------------------------------------------
# Signed out
# --------------------------------------------------------------------------------------


@requires_db
@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/chat-sessions"),
        ("POST", "/chat-sessions"),
        ("GET", "/chat-sessions/{id}"),
        ("PUT", "/chat-sessions/{id}"),
        ("DELETE", "/chat-sessions/{id}"),
    ],
)
def test_every_route_requires_a_signed_in_user(two_users, method, path):
    """No route may answer without a session cookie. Parameterised over all five rather than
    spot-checked, because the failure mode is one route being added or edited without the
    dependency — which a test of the other four would not catch."""
    from app.main import app

    alice, _ = two_users
    chat = alice.create_chat("Alice's client")
    url = path.format(id=chat["id"])

    with TestClient(app) as anonymous:  # its own cookie jar: never signed in
        res = anonymous.request(method, url, json={"title": "x", "state": {}})
    assert res.status_code == 401, f"{method} {path} answered {res.status_code} while signed out"


@requires_db
def test_signing_out_ends_access_to_the_history(two_users):
    """The shared-machine case: after sign-out the same browser must not still read the list."""
    alice, _ = two_users
    alice.create_chat("Alice's client")
    assert len(alice.list_chats()) == 1

    assert alice.client.post("/auth/logout").status_code == 200
    assert alice.client.get("/chat-sessions").status_code == 401


@requires_db
def test_signing_back_in_restores_the_same_history(two_users):
    """Isolation must not be amnesia — the other half of the requirement. A user's own chats come
    back on the next sign-in, which is what distinguishes this from clearing the table."""
    alice, _ = two_users
    alice.create_chat("Alice's client")
    alice.client.post("/auth/logout")

    res = alice.client.post("/auth/login", json={"email": alice.email, "password": "correct horse"})
    assert res.status_code == 200, res.text
    assert [c["title"] for c in alice.list_chats()] == ["Alice's client"]


# --------------------------------------------------------------------------------------
# The Phase 2 parent-run picker, which leaked the same data by another route
# --------------------------------------------------------------------------------------


@requires_db
def test_source_runs_requires_a_signed_in_user():
    from app.main import app

    with TestClient(app) as anonymous:
        assert anonymous.get("/pipeline/source-runs").status_code == 401


@requires_db
def test_source_runs_does_not_offer_another_users_runs(two_users):
    """`GET /pipeline/source-runs` named every run in the installation by company name, so Phase 2
    let one operator inherit another's ICP and page copy. It is scoped through the owning chat.

    Both directions are asserted. "Bob cannot see it" alone would pass against a route that
    returned `[]` to everybody, which would break the picker instead of scoping it — so Alice's own
    run has to still be offered to Alice in the same test.

    Asserted by run id rather than by list length, so the result does not depend on whatever else
    is in a shared development database.
    """
    alice, bob = two_users
    alice_chat = alice.create_chat("Alice's client")
    run_id = _fixture_run(alice)

    # Claim the run on Alice's chat, the way the frontend's autosave does.
    attached = alice.client.put(
        f"/chat-sessions/{alice_chat['id']}",
        json={"title": "Alice's client", "state": {"runId": run_id}},
    )
    assert attached.status_code == 200, attached.text
    # The claim is *skipped*, not refused, when the run is already taken, so a 200 does not prove
    # the FK column was written — and the state blob echoes back whatever was PUT either way. Read
    # the column itself, so a stale claim fails here with its own cause rather than surfacing below
    # as "scoping is broken".
    assert _chat_run_id(alice_chat["id"]) == run_id, (
        "the chat did not claim the run — something else still holds it"
    )

    bob_res = bob.client.get("/pipeline/source-runs")
    assert bob_res.status_code == 200, bob_res.text
    assert run_id not in {row["run_id"] for row in bob_res.json()}

    alice_res = alice.client.get("/pipeline/source-runs")
    assert alice_res.status_code == 200, alice_res.text
    assert run_id in {row["run_id"] for row in alice_res.json()}
