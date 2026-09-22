"""Tests for `app/services/media_storage.py` — Postgres-backed storage for OpenAI's generated
bytes.

See that module's docstring for why this exists at all: OpenAI's image models return base64, not
a hosted URL the way Runway's did, so something has to turn the bytes into a link a prompt can
reference without echoing thousands of characters of base64 into the model's own output — and why
that something is Postgres rather than local disk (this app deploys to Railway, where local disk
is the container's own ephemeral disk).

This backend's tests do not have Postgres (see `test_standalone_runs.py`), so `save_generated_image`
is tested against a minimal fake session that only implements the one method it actually calls —
`add()` — the same seam every other DB-touching test in this suite uses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.db.models import MediaAsset
from app.services import media_storage


@dataclass
class _FakeSession:
    added: list[Any] = field(default_factory=list)

    def add(self, obj: Any) -> None:
        self.added.append(obj)


def test_save_generated_image_stages_a_media_asset_and_returns_its_url(monkeypatch):
    monkeypatch.delenv(media_storage.PUBLIC_BASE_URL_ENV, raising=False)
    session = _FakeSession()

    url = media_storage.save_generated_image(session, b"fake-png-bytes", output_format="png")

    assert url.startswith("http://127.0.0.1:8001/media/")
    assert len(session.added) == 1
    asset = session.added[0]
    assert isinstance(asset, MediaAsset)
    assert asset.data == b"fake-png-bytes"
    assert asset.content_type == "image/png"
    assert str(asset.id) in url


def test_save_generated_image_respects_a_configured_public_base_url(monkeypatch):
    monkeypatch.setenv(media_storage.PUBLIC_BASE_URL_ENV, "https://api.example.com/")
    session = _FakeSession()

    url = media_storage.save_generated_image(session, b"x", output_format="webp")

    assert url.startswith("https://api.example.com/media/")
    assert session.added[0].content_type == "image/webp"


def test_two_saves_never_collide_on_id():
    session = _FakeSession()

    first = media_storage.save_generated_image(session, b"a", output_format="png")
    second = media_storage.save_generated_image(session, b"b", output_format="png")

    assert first != second
    assert session.added[0].id != session.added[1].id
