"""creating foreign key reference for sku from potions to potion_ledger

Revision ID: a7b4d2bc2d17
Revises: dabdabae792c
Create Date: 2025-05-08 11:50:25.064762

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7b4d2bc2d17'
down_revision: Union[str, None] = 'dabdabae792c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_foreign_key(
        'fk_potion_ledger_sku_potions',  
        'potion_ledger',                  # table we want to create FK at
        'potions',                        # table being referenced
        ['sku'],
        ['sku'],
        ondelete='RESTRICT'               # prevent deletion if referenced
    )

def downgrade() -> None:
    op.drop_constraint(
        'fk_potion_ledger_sku_potions',
        'potion_ledger',
        type_='foreignkey'
    )
