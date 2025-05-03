"""remove_unique_order_id_constraint

Revision ID: dabdabae792c
Revises: 8cade2ad07bf
Create Date: 2025-05-03 00:01:35.658722

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dabdabae792c'
down_revision: Union[str, None] = '8cade2ad07bf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('gold_ledger_order_id_key', 'gold_ledger', type_='unique')
    op.drop_constraint('liquid_ledger_order_id_key', 'liquid_ledger', type_='unique')

def downgrade() -> None:
    op.create_unique_constraint('gold_ledger_order_id_key', 'gold_ledger', ['order_id'])
    op.create_unique_constraint('liquid_ledger_order_id_key', 'liquid_ledger', ['order_id'])