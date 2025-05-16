"""rename_tick_number_to_hour

Revision ID: 202405161501
Revises: 202405161500
Create Date: 2024-05-16 15:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '202405161501'
down_revision: Union[str, None] = '202405161500'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('sale_analytics', 'tick_number', 
                    new_column_name='hour_of_day',
                    existing_type=sa.Integer,
                    nullable=False)


def downgrade() -> None:
    op.alter_column('sale_analytics', 'hour_of_day', 
                    new_column_name='tick_number',
                    existing_type=sa.Integer,
                    nullable=False)
