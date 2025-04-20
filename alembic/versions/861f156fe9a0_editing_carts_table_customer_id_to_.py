"""redoing carts and cart_item table

Revision ID: 861f156fe9a0
Revises: 20926ec8fc57
Create Date: 2025-04-20 10:55:02.148029

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '861f156fe9a0'
down_revision: Union[str, None] = '20926ec8fc57'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'carts',
        sa.Column("cart_id", sa.Integer, primary_key=True),
        sa.Column("customer_name", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column("is_checked_out", sa.Boolean, server_default="false")
    )
    op.create_table(
        'cart_items',
        sa.Column("cart_item_id", sa.Integer, primary_key=True),
        sa.Column("cart_id", sa.Integer, nullable=False),
        sa.Column("sku", sa.String, nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(['cart_id'], ['carts.cart_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sku'], ['potions.sku'], ondelete='CASCADE')
    )
    op.create_unique_constraint(
        'cart_items_cart_id_sku_key',
        'cart_items',
        ['cart_id', 'sku']
    )

def downgrade() -> None:
    op.drop_table('carts')
    op.drop_table('cart_items')
