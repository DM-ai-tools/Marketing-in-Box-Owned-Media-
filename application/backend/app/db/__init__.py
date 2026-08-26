"""Persistence layer: SQLAlchemy models, session/engine setup, and Alembic migrations.

See app/db/SCHEMA.md for the full table-by-table rationale.
"""

from app.db.base import Base

__all__ = ["Base"]
