"""add refund payment filename

Revision ID: f76d3be18936
Revises: bc9699597a1c
Create Date: 2026-07-30 12:55:41.877541

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f76d3be18936'
down_revision: Union[str, Sequence[str], None] = 'bc9699597a1c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('refunds', sa.Column('payment_filename', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('refunds', 'payment_filename')
