"""add cart items and sku unique constraint

Revision ID: b4b336f23567
Revises: 49d93535ed8e
Create Date: 2025-04-19 03:01:54.276462

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4b336f23567'
down_revision: Union[str, None] = '49d93535ed8e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        'cart_items_cart_id_sku_key',
        'cart_items',
        ['cart_id', 'sku']
    )
    op.crea


def downgrade() -> None:
    op.drop_constraint(
        'cart_items_cart_id_sku_key',
        'cart_items',
        type_='unique'
    )
