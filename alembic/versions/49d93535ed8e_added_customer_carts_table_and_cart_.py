"""added customer carts table and cart items table

Revision ID: 49d93535ed8e
Revises: 6266cd89be31
Create Date: 2025-04-18 20:12:50.243666

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '49d93535ed8e'
down_revision: Union[str, None] = '6266cd89be31'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'carts',
        sa.Column("cart_id", sa.Integer, primary_key=True),
        sa.Column("customer_id", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column("is_checked_out", sa.Boolean, server_default="false")
    )
    op.create_table(
        'cart_items',
        sa.Column("cart_item_id", sa.Integer, primary_key=True, server_default="0"),
        sa.Column("cart_id", sa.Integer, nullable=False),
        sa.Column("sku", sa.String, nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(['cart_id'], ['carts.cart_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sku'], ['potions.sku'], ondelete='CASCADE')
    )


def downgrade() -> None:
    op.drop_table('cart_items')
    op.drop_table('carts')

