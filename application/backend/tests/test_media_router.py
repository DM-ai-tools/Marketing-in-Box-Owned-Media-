"""Tests for `GET /media/{id}` (`app/routers/media.py`).

Nothing here touches Postgres — this backend's tests do not have it (see
`test_standalone_runs.py`), so `get_sessionmaker` is faked at the same seam every other
DB-touching route test in this suite uses.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from fastapi.testclient import TestClient

from app.main import app
from app.routers import media as media_router

ASSET_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


@dataclass
class _FakeAsset:
    id: uuid.UUID
    data: bytes
    content_type: str


class _FakeSession:
    def __init__(self, asset: _FakeAsset | None):
        self._asset = asset

    async def get(self, _model: Any, ident: Any) -> Any:
        return self._asset if self._asset is not None and ident == self._asset.id else None

    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, *_exc: Any) -> bool:
        return False


def _client_with(asset: _FakeAsset | None, monkeypatch) -> TestClient:
    monkeypatch.setattr(media_router, "get_sessionmaker", lambda: (lambda: _FakeSession(asset)))
    return TestClient(app)


def test_serves_the_bytes_with_the_stored_content_type(monkeypatch):
    asset = _FakeAsset(id=ASSET_ID, data=b"fake-png-bytes", content_type="image/png")
    client = _client_with(asset, monkeypatch)

    response = client.get(f"/media/{ASSET_ID}")

    assert response.status_code == 200
    assert response.content == b"fake-png-bytes"
    assert response.headers["content-type"] == "image/png"


def test_unknown_id_is_a_404(monkeypatch):
    client = _client_with(None, monkeypatch)

    response = client.get(f"/media/{ASSET_ID}")

    assert response.status_code == 404


def test_a_non_uuid_path_segment_is_a_404_not_a_500(monkeypatch):
    client = _client_with(None, monkeypatch)

    response = client.get("/media/not-a-uuid")

    assert response.status_code == 404
