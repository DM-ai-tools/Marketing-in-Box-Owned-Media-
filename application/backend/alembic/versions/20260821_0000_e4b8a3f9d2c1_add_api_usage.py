"""add api_usage

Revision ID: e4b8a3f9d2c1
Revises: d7c31b8e5a92
Create Date: 2026-08-21 00:00:00

Per-call token and cost accounting for the Anthropic API, attributed to the chat that spent it.
Nothing else in the schema carries this: `context_entries` records what a stage produced, not what
producing it consumed, and a stage generated three times and approved once leaves one context row
against three billed calls.

Both foreign keys are nullable and `SET NULL` on delete. A usage row is a financial record and has
to outlive the chat and the run that incurred it — otherwise deleting a chat silently reduces a
past month's total. Nullable also covers the real gap at write time: a chat's session row exists
before its run does, and the first call of a brand-new chat can precede both.

`cost_usd` is stored rather than computed on read, with `rates_version` naming the price table that
produced it — see `app/services/pricing.py`. List prices change, and a total that moves when a rate
changes cannot be reconciled against an invoice.

Hand-authored, matching every prior migration in this project.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PGUUID

# revision identifiers, used by Alembic.
revision: str = "e4b8a3f9d2c1"
down_revision: Union[str, None] = "d7c31b8e5a92"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "api_usage",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column(
            "chat_session_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("chat_sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("run_id", PGUUID(as_uuid=True), sa.ForeignKey("runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("asset_id", sa.String(length=100), nullable=True),
        sa.Column("phase", sa.String(length=20), nullable=True),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("model", sa.String(length=80), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "cache_creation_input_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("cache_read_input_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("web_search_requests", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("rates_version", sa.String(length=20), nullable=False),
        sa.Column("stop_reason", sa.String(length=40), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_api_usage_chat_session_id", "api_usage", ["chat_session_id"])
    op.create_index("ix_api_usage_created_at", "api_usage", ["created_at"])
    op.create_index("ix_api_usage_run_id", "api_usage", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_api_usage_run_id", table_name="api_usage")
    op.drop_index("ix_api_usage_created_at", table_name="api_usage")
    op.drop_index("ix_api_usage_chat_session_id", table_name="api_usage")
    op.drop_table("api_usage")
