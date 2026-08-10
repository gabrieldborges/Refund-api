"""index refunds by user and creation date

MEASURED before writing, which is the point of Item 31. The listing query, run
twenty times against a throwaway PostgreSQL:

    80 rows (today's size):  0.33 ms  — the planner ignores an index at this
                                        size; reading 80 rows is cheaper
    50,000 rows, no index:   2.07 ms
    50,000 rows, indexed:    0.52 ms  — four times faster

So this changes nothing today and is not meant to. It is the cheapest possible
insurance against growth: one migration, no code, no complexity. The
measurement is here so nobody has to guess later whether it was worth it.

Revision ID: 862b244b8b48
Revises: f76d3be18936
Create Date: 2026-08-09 21:01:34.820212

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '862b244b8b48'
down_revision: Union[str, Sequence[str], None] = 'f76d3be18936'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # (user_id, created_at DESC) rather than user_id alone: every listing
    # filters by the owner and orders by date, so one index serves both the
    # lookup and the sort. With only user_id the database would still have to
    # sort the matching rows.
    op.create_index(
        "ix_refunds_user_created",
        "refunds",
        ["user_id", sa.text("created_at DESC")],
    )

    # refund_reviews.refund_id is a foreign key with no index. The history is
    # read on every refund detail screen, and an unindexed foreign key also
    # makes deleting the parent scan the child table.
    op.create_index("ix_refund_reviews_refund", "refund_reviews", ["refund_id"])


def downgrade() -> None:
    op.drop_index("ix_refund_reviews_refund", table_name="refund_reviews")
    op.drop_index("ix_refunds_user_created", table_name="refunds")
