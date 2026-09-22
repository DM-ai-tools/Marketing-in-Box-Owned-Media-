"""add media_assets

Revision ID: c8d914e6a5b3
Revises: b6e2f04a9d18
Create Date: 2026-09-22 00:00:00

Storage for OpenAI-generated brand images (`app/services/image_briefs.py` /
`app/services/openai_image_client.py`), served back at `GET /media/{id}` (`app/routers/media.py`).

This is the one table in this schema that stores raw bytes rather than a reference to something
regenerable or externally hosted — see `MediaAsset`'s own docstring in `app/db/models.py` for why:
in short, this app deploys to Railway, where local disk is the container's own ephemeral disk, and
even a persistent Railway Volume cannot be combined with more than one replica. Postgres is
already durable and already multi-instance-safe, so the bytes go here rather than adding a second
storage dependency for what is, per run, three small files.

Hand-authored, matching every prior migration in this project.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PGUUID

# revision identifiers, used by Alembic.
revision: str = "c8d914e6a5b3"
down_revision: Union[str, None] = "b6e2f04a9d18"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "media_assets",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_media_assets_created_at", "media_assets", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_media_assets_created_at", table_name="media_assets")
    op.drop_table("media_assets")
