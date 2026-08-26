"""add users, login sessions, password reset tokens

Revision ID: f2a71c9d4e83
Revises: e4b8a3f9d2c1
Create Date: 2026-08-26 00:00:00

Three tables behind the sign-in gate — email and password only; there is no federated/OAuth
identity in this schema. Split by lifetime rather than folded into one wide `users` row: an
account is permanent, a login session is revocable and expires, and a reset token is single-use.
See the "Authentication tables" section of app/db/models.py for the rationale on each.

Notes on the choices this migration hard-codes:

- `users.password_hash` is NOT NULL. A password is the only way into this system, so an account
  without one could never be signed in to and has no reason to exist.
- `users.email` gets a single UNIQUE index on an already-lowercased column, not a functional
  `lower(email)` index — and not a UniqueConstraint *plus* an index, see the note in `upgrade`.
  Normalization happens in one place in the application (`auth.normalize_email`), and a
  case-sensitive unique index would happily create a second account for the same person.
- Both token tables store a SHA-256 hex digest in a `String(64)`, never the token. A dump of this
  schema cannot be replayed as a login.
- Every FK is `ON DELETE CASCADE`. Unlike `api_usage`, neither of these is a record that must
  outlive its user: deleting an account should take its logins and its pending reset links with
  it, and leaving either behind would be a live credential for an account that no longer exists.

Hand-authored, matching every prior migration in this project.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PGUUID

# revision identifiers, used by Alembic.
revision: str = "f2a71c9d4e83"
down_revision: Union[str, None] = "e4b8a3f9d2c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=True),
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    # A single UNIQUE index, not a UniqueConstraint plus a plain index. The two are functionally
    # equivalent in Postgres, but the ORM model declares `unique=True, index=True` on the column —
    # which renders as one unique index — and anything else here is schema drift that `alembic
    # check` reports forever. Same for both `token_hash` columns below.
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "user_sessions",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # SHA-256 hex of the cookie value, never the value.
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.String(length=400), nullable=True),
    )
    # The lookup on every authenticated request, and the uniqueness guarantee, in one index.
    op.create_index("ix_user_sessions_token_hash", "user_sessions", ["token_hash"], unique=True)
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    # Supports the "expired rows are deleted on sight" grooming in `auth.resolve_session`.
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"])

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        # NULL until redeemed; stamping it is what makes the token single-use.
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"], unique=True
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_password_reset_tokens_user_id", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_token_hash", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")

    op.drop_index("ix_user_sessions_expires_at", table_name="user_sessions")
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_index("ix_user_sessions_token_hash", table_name="user_sessions")
    op.drop_table("user_sessions")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
