"""add competitors.category

Revision ID: d7c31b8e5a92
Revises: c5a92f1e7b46
Create Date: 2026-08-20 01:00:00

Three of the competitor prompts classify each competitor with one short label, and the operator
scans that label down the listing: `03_Lead_Magnet.md` reports the lead-magnet type ("Gated ebook",
"Calculator"), `04_Blog.md` the blog's content focus, `10_Podcast.md` the episode's topical focus.

One shared column rather than three stage-specific ones, because no prompt emits more than one such
label and per-stage columns would leave seven of the ten stages with dead fields. See the column's
comment in `app/db/models.py`.

Nullable with no default: the stages that classify nothing leave it null.

Hand-authored, matching every prior migration in this project.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d7c31b8e5a92"
down_revision: Union[str, None] = "c5a92f1e7b46"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("competitors", sa.Column("category", sa.String(length=160), nullable=True))


def downgrade() -> None:
    op.drop_column("competitors", "category")
