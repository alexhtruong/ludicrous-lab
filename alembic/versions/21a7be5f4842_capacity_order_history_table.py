"""capacity order history table

Revision ID: 21a7be5f4842
Revises: 7659d41cb1b3
Create Date: 2025-04-30 19:52:36.694100

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '21a7be5f4842'
down_revision: Union[str, None] = '7659d41cb1b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'capacity_order_ledger',
        sa.Column('ledger_id', sa.Integer, primary_key=True),
        sa.Column('order_id', sa.Integer, unique=True, nullable=False),
        sa.Column('potion_capacity_increase', sa.Integer, nullable=False),
        sa.Column('ml_capacity_increase', sa.Integer, nullable=False),
        sa.Column('gold_delta', sa.Integer, nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
    )


def downgrade() -> None:
    op.drop_table('capacity_order_ledger')
