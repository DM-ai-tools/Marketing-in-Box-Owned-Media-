"""add competitors.starting_price

Revision ID: c5a92f1e7b46
Revises: b8f31d2a6c94
Create Date: 2026-08-20 00:00:00

The Offers / Value Ladder stage's competitor sub-step (`competitor_analysis_offers`, running
`assets/Prompts/Competitor Analysis/02_Offers.md`) reports each competitor's published starting
price, which the operator reviews in the listing and which then feeds the value-ladder prompt.
Nothing else in the schema could hold it.

Text rather than Numeric on purpose — see the column's comment in `app/db/models.py`: competitors
publish "From $1,500/mo", "$990 setup + $2,400/mo", "$4,500 one-off", and the unit, the qualifier
and the "from" are the informative parts. A numeric column would force the parser to discard them,
or worse, to invent a single figure where a band was published, and this value flows into the
client's own pricing decisions.

Nullable with no default: the other nine competitor stages have no price to report, and a
competitor that publishes tiers but no figure is a real, reportable case.

Hand-authored, matching every prior migration in this project.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c5a92f1e7b46"
down_revision: Union[str, None] = "b8f31d2a6c94"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("competitors", sa.Column("starting_price", sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column("competitors", "starting_price")
