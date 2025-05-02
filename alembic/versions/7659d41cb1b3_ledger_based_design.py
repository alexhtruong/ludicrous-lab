"""ledger-based design

Revision ID: 7659d41cb1b3
Revises: d409de638516
Create Date: 2025-04-29 22:06:02.915830

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7659d41cb1b3'
down_revision: Union[str, None] = 'd409de638516'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'liquid_ledger',
        sa.Column('ledger_id', sa.Integer, primary_key=True),
        sa.Column('order_id', sa.String, unique=True, nullable=False),
        sa.Column('red_ml_delta', sa.Integer, nullable=False),
        sa.Column('green_ml_delta', sa.Integer, nullable=False),
        sa.Column('blue_ml_delta', sa.Integer, nullable=False),
        sa.Column('dark_ml_delta', sa.Integer, nullable=False),
        sa.Column('transaction_type', sa.String, nullable=False),  # 'BARREL_DELIVERY', 'POTION_CREATION'
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.UniqueConstraint('order_id', 'transaction_type', name='uix_liquid_ledger_order_type')
    )

    op.create_table(
        'gold_ledger',
        sa.Column('ledger_id', sa.Integer, primary_key=True),
        sa.Column('order_id', sa.String, unique=True, nullable=False),
        sa.Column('gold_delta', sa.Integer, nullable=False),  
        sa.Column('transaction_type', sa.String, nullable=False),  # 'BARREL_PURCHASE', 'POTION_SALE'
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_table(
        'potion_ledger',
        sa.Column('ledger_id', sa.Integer, primary_key=True),
        sa.Column('order_id', sa.String, nullable=False),
        sa.Column('line_item_id', sa.Integer, nullable=False), # line_item_id: 1, 2, 3... allows for multiple skus per order
        sa.Column('sku', sa.String, nullable=False),
        sa.Column('quantity_delta', sa.Integer, nullable=False),  
        sa.Column('transaction_type', sa.String, nullable=False),  # 'POTION_CREATION', 'POTION_SALE'
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.UniqueConstraint('order_id', 'line_item_id', name='uix_potion_ledger_order_sku')
    )


def downgrade() -> None:
    op.drop_table('liquid_ledger')
    op.drop_table('gold_ledger')
    op.drop_table('potion_ledger')
        
