"""removing columns

Revision ID: c76f9e7aa2b4
Revises: a7b4d2bc2d17
Create Date: 2025-05-09 19:14:16.799807

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c76f9e7aa2b4'
down_revision: Union[str, None] = 'a7b4d2bc2d17'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('global_inventory', 'red_ml')
    op.drop_column('global_inventory', 'green_ml')
    op.drop_column('global_inventory', 'blue_ml')
    op.drop_column('global_inventory', 'dark_ml')
    op.drop_column('global_inventory', 'gold')
    op.drop_column('potions', 'quantity')
    op.drop_column('potions', 'updated_at')


def downgrade() -> None:
    op.add_column(
        'global_inventory',
        sa.Column('gold', sa.Integer(), nullable=False, server_default='100'),
    )
    op.add_column(
        'global_inventory',
        sa.Column('blue_ml', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column(
        'global_inventory',
        sa.Column('green_ml', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column(
        'global_inventory',
        sa.Column('red_ml', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column(
        'global_inventory',
        sa.Column('dark_ml', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column(
        'potions',
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column(
        'potions',
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

