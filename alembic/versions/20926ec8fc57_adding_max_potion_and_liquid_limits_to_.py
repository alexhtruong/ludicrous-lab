"""adding max potion and liquid limits to global_inventory table

Revision ID: 20926ec8fc57
Revises: 94f7736daffe
Create Date: 2025-04-20 00:40:53.617245

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20926ec8fc57'
down_revision: Union[str, None] = '94f7736daffe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('global_inventory', sa.Column('max_potion_capacity', sa.Integer(), nullable=False, server_default="50"))
    op.add_column('global_inventory', sa.Column('max_barrel_capacity', sa.Integer(), nullable=False, server_default="10000"))


def downgrade() -> None:
    op.drop_column('global_inventory', 'max_potion_capacity')
    op.drop_column('global_inventory', 'max_barrel_capacity')

