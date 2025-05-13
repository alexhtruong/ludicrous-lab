"""change_liquid_ledger_order_id_to_integer

Revision ID: a8340815cd45
Revises: c76f9e7aa2b4
Create Date: 2025-05-09 20:44:24.934870

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8340815cd45'
down_revision: Union[str, None] = 'c76f9e7aa2b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('uix_liquid_ledger_order_type', 'liquid_ledger')
    
    op.alter_column('liquid_ledger', 'order_id',
                    type_=sa.Integer,
                    postgresql_using='order_id::integer',
                    existing_type=sa.String,
                    existing_nullable=False)
    
    op.create_unique_constraint('uix_liquid_ledger_order_type', 'liquid_ledger', ['order_id', 'transaction_type'])

    op.alter_column('gold_ledger', 'order_id',
                    type_=sa.Integer,
                    postgresql_using='order_id::integer',
                    existing_type=sa.String,
                    existing_nullable=False)

    op.drop_constraint('uix_potion_ledger_order_sku', 'potion_ledger')
    
    op.alter_column('potion_ledger', 'order_id',
                    type_=sa.Integer,
                    postgresql_using='order_id::integer',
                    existing_type=sa.String,
                    existing_nullable=False)
    
    op.create_unique_constraint('uix_potion_ledger_order_sku', 'potion_ledger', ['order_id', 'line_item_id'])

def downgrade() -> None:
    op.drop_constraint('uix_liquid_ledger_order_type', 'liquid_ledger')
    
    op.alter_column('liquid_ledger', 'order_id',
                    type_=sa.String,
                    postgresql_using='order_id::text',
                    existing_type=sa.Integer,
                    existing_nullable=False)
    
    op.create_unique_constraint('uix_liquid_ledger_order_type', 'liquid_ledger', ['order_id', 'transaction_type'])
    
    op.alter_column('gold_ledger', 'order_id',
                    type_=sa.String,
                    postgresql_using='order_id::text',
                    existing_type=sa.Integer,
                    existing_nullable=False)

    op.drop_constraint('uix_potion_ledger_order_sku', 'potion_ledger')
    
    op.alter_column('potion_ledger', 'order_id',
                    type_=sa.String,
                    postgresql_using='order_id::text',
                    existing_type=sa.Integer,
                    existing_nullable=False)
    
    op.create_unique_constraint('uix_potion_ledger_order_sku', 'potion_ledger', ['order_id', 'line_item_id'])