"""add dark_ml column to global_inventory

Revision ID: 6266cd89be31
Revises: 56b5ec80be3b
Create Date: 2025-04-18 11:22:26.684559

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6266cd89be31'
down_revision: Union[str, None] = '56b5ec80be3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("global_inventory", sa.Column("dark_ml", sa.Integer(), nullable=False, server_default="0"))
    op.create_check_constraint("ck_dark_ml_non_negative", "global_inventory", "dark_ml >= 0")



def downgrade() -> None:
    op.drop_column("global_inventory", "dark_ml")
    op.drop_constraint("ck_dark_ml_non_negative", "global_inventory", type_="check")
