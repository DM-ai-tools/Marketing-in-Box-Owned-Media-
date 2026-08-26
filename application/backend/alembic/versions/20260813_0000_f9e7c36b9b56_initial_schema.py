"""initial schema

Revision ID: f9e7c36b9b56
Revises:
Create Date: 2026-08-13 00:00:00

Creates the full Postgres schema described in app/db/models.py / app/db/SCHEMA.md:
- Core: asset_definitions, clients, runs, run_stages, context_entries, approval_audit_log,
  prompt_recipes
- Conversational Intake Engine: field_schema_registry, field_sessions, attachments

Hand-authored rather than produced by `alembic revision --autogenerate`: this is a fresh
database with no live Postgres instance available in the dev sandbox to autogenerate against
(autogenerate requires reflecting an existing connection, even offline). Every column, type,
constraint, and index below was cross-checked against `app/db/models.py` by compiling its
`CreateTable`/`CreateIndex` DDL through the postgresql dialect, so this migration is the exact
DDL SQLAlchemy would emit for these models.

Tables are created in dependency order (parents before children with FKs to them) and dropped
in reverse order in `downgrade()`.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f9e7c36b9b56"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Enum type definitions (created explicitly before use — op.create_table does not auto-emit
# CREATE TYPE the way MetaData.create_all() does).
_run_status = postgresql.ENUM(
    "IN_PROGRESS", "COMPLETED", "PAUSED", "CANCELLED", name="run_status"
)
_stage_status = postgresql.ENUM(
    "NOT_STARTED",
    "COLLECTING",
    "READY_FOR_GENERATION",
    "CONFIRMED",
    "DRAFTING",
    "AWAITING_REVIEW",
    "APPROVED",
    "REJECTED",
    name="stage_status",
)
_field_session_status = postgresql.ENUM(
    "NOT_STARTED",
    "COLLECTING",
    "READY_FOR_GENERATION",
    "CONFIRMED",
    name="field_session_status",
)
_audit_action = postgresql.ENUM("APPROVED", "REJECTED", "EDITED", name="audit_action")

# Trigger function shared by the two append-only tables (context_entries,
# field_schema_registry): raises on any UPDATE or DELETE, so "additive, never overwritten"
# (Session Context Sec. 6) and "immutable once referenced by a run" (Intake design Sec. 3)
# are enforced by Postgres itself, not just by ORM discipline.
_BLOCK_MUTATION_FN = """
CREATE OR REPLACE FUNCTION block_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'Table % is append-only: % is not permitted', TG_TABLE_NAME, TG_OP
        USING ERRCODE = 'restrict_violation';
END;
$$ LANGUAGE plpgsql;
"""


def upgrade() -> None:
    bind = op.get_bind()

    for enum_type in (_run_status, _stage_status, _field_session_status, _audit_action):
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "asset_definitions",
        sa.Column("asset_id", sa.String(length=100), primary_key=True),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("phase", sa.SmallInteger(), nullable=False),
        sa.Column("sequence_order", sa.SmallInteger(), nullable=False),
        sa.Column("is_gated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "depends_on",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "reads_context_keys",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "writes_context_keys",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("phase IN (1, 2)", name="ck_asset_definitions_phase"),
        sa.UniqueConstraint("phase", "sequence_order", name="uq_asset_definitions_phase_order"),
    )

    op.create_table(
        "clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_name", sa.String(length=300), nullable=False),
        sa.Column("industry", sa.String(length=200), nullable=True),
        sa.Column("region", sa.String(length=200), nullable=True),
        sa.Column("service_focus", sa.String(length=500), nullable=True),
        sa.Column(
            "known_competitors",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "field_schema_registry",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "asset_id",
            sa.String(length=100),
            sa.ForeignKey("asset_definitions.asset_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("version", sa.SmallInteger(), nullable=False),
        sa.Column("schema_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("asset_id", "version", name="uq_field_schema_registry_asset_version"),
    )

    op.create_table(
        "prompt_recipes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "asset_id",
            sa.String(length=100),
            sa.ForeignKey("asset_definitions.asset_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("version", sa.SmallInteger(), nullable=False),
        sa.Column("recipe_body", sa.Text(), nullable=False),
        sa.Column("source_file", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("asset_id", "version", name="uq_prompt_recipes_asset_version"),
    )
    op.create_index(
        "uq_prompt_recipes_one_active_per_asset",
        "prompt_recipes",
        ["asset_id"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )

    op.create_table(
        "runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "source_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(name="run_status", create_type=False),
            nullable=False,
            server_default="IN_PROGRESS",
        ),
        sa.Column(
            "current_stage_id",
            sa.String(length=100),
            sa.ForeignKey("asset_definitions.asset_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_runs_client_id", "runs", ["client_id"])

    op.create_table(
        "approval_audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "asset_id",
            sa.String(length=100),
            sa.ForeignKey("asset_definitions.asset_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("action", postgresql.ENUM(name="audit_action", create_type=False), nullable=False),
        sa.Column("actor", sa.String(length=300), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("diff_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_approval_audit_log_run_asset", "approval_audit_log", ["run_id", "asset_id"])
    op.create_index("ix_approval_audit_log_created_at", "approval_audit_log", ["created_at"])

    op.create_table(
        "context_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("context_key", sa.String(length=200), nullable=False),
        sa.Column("version", sa.SmallInteger(), nullable=False, server_default=sa.text("1")),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "written_by_asset_id",
            sa.String(length=100),
            sa.ForeignKey("asset_definitions.asset_id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "run_id", "context_key", "version", name="uq_context_entries_run_key_version"
        ),
    )
    op.create_index("ix_context_entries_run_key", "context_entries", ["run_id", "context_key"])

    op.create_table(
        "field_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stage_id", sa.String(length=100), nullable=False),
        sa.Column("schema_version", sa.SmallInteger(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(name="field_session_status", create_type=False),
            nullable=False,
            server_default="NOT_STARTED",
        ),
        sa.Column(
            "resolved_fields",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "pending_field_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "transcript",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["stage_id", "schema_version"],
            ["field_schema_registry.asset_id", "field_schema_registry.version"],
            name="fk_field_sessions_schema_registry",
            ondelete="RESTRICT",
        ),
    )
    op.create_index("ix_field_sessions_run_stage", "field_sessions", ["run_id", "stage_id"])
    op.create_index(
        "uq_field_sessions_one_open_per_stage",
        "field_sessions",
        ["run_id", "stage_id"],
        unique=True,
        postgresql_where=sa.text("status != 'CONFIRMED'"),
    )

    op.create_table(
        "run_stages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "asset_id",
            sa.String(length=100),
            sa.ForeignKey("asset_definitions.asset_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(name="stage_status", create_type=False),
            nullable=False,
            server_default="NOT_STARTED",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("run_id", "asset_id", name="uq_run_stages_run_asset"),
    )
    op.create_index("ix_run_stages_asset_status", "run_stages", ["asset_id", "status"])

    op.create_table(
        "attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "field_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("field_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field_id", sa.String(length=200), nullable=False),
        sa.Column("storage_url", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(length=150), nullable=False),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_attachments_session_field", "attachments", ["field_session_id", "field_id"])

    # --- Append-only enforcement -------------------------------------------------------
    # context_entries: "Context keys are additive, never overwritten" (Session Context Sec. 6).
    # field_schema_registry: "Immutable once referenced by a run" (Intake design Sec. 3).
    op.execute(_BLOCK_MUTATION_FN)
    for table_name in ("context_entries", "field_schema_registry"):
        op.execute(
            f"""
            CREATE TRIGGER {table_name}_block_mutation
            BEFORE UPDATE OR DELETE ON {table_name}
            FOR EACH ROW EXECUTE FUNCTION block_mutation();
            """
        )


def downgrade() -> None:
    for table_name in ("context_entries", "field_schema_registry"):
        op.execute(f"DROP TRIGGER IF EXISTS {table_name}_block_mutation ON {table_name};")
    op.execute("DROP FUNCTION IF EXISTS block_mutation();")

    op.drop_table("attachments")
    op.drop_table("run_stages")
    op.drop_table("field_sessions")
    op.drop_table("context_entries")
    op.drop_table("approval_audit_log")
    op.drop_table("runs")
    op.drop_table("prompt_recipes")
    op.drop_table("field_schema_registry")
    op.drop_table("clients")
    op.drop_table("asset_definitions")

    bind = op.get_bind()
    for enum_type in (_field_session_status, _audit_action, _stage_status, _run_status):
        enum_type.drop(bind, checkfirst=True)
