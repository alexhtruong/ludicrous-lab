"""add_analytics_tables

Revision ID: 20b89b903e2f
Revises: a8340815cd45
Create Date: 2025-05-15 13:31:38.005417

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20b89b903e2f'
down_revision: Union[str, None] = 'a8340815cd45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'sale_analytics',
        sa.Column('transaction_id', sa.Integer, primary_key=True),
        sa.Column('cart_id', sa.Integer, nullable=False),
        sa.Column('customer_class', sa.String, nullable=False),
        sa.Column('tick_number', sa.Integer, nullable=False),
        sa.Column('day_of_week', sa.String, nullable=False),
        sa.Column('total_gold', sa.Float, nullable=False),
        sa.Column('potion_count', sa.Integer, nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_table(
        'potion_analytics',
        sa.Column('sku', sa.String, primary_key=True),
        sa.Column('total_sales', sa.Integer, nullable=False, server_default='0'),
        sa.Column('total_gold', sa.Float, nullable=False, server_default='0'),
        sa.Column('avg_sale_price', sa.Float, nullable=False, server_default='0'),
        sa.Column('profit_margin', sa.Float, nullable=False, server_default='0'),
        sa.Column('last_updated', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['sku'], ['potions.sku'], ondelete='CASCADE')
    )

    op.create_table(
        'time_analytics',
        sa.Column('tick_id', sa.Integer, primary_key=True),
        sa.Column('day_of_week', sa.String, nullable=False),
        sa.Column('tick_of_day', sa.Integer, nullable=False),
        sa.Column('total_sales', sa.Integer, nullable=False, server_default='0'),
        sa.Column('total_gold', sa.Float, nullable=False, server_default='0'),
        sa.Column('stock_out_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('visitor_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP'))
    )


def downgrade() -> None:
    op.drop_table('time_analytics')
    op.drop_table('potion_analytics') 
    op.drop_table('sale_analytics')
