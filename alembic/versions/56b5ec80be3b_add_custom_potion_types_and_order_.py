"""Add custom potion types and order management

Revision ID: 56b5ec80be3b
Revises: aad06a393a3b
Create Date: 2025-04-16 11:32:04.663041

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '56b5ec80be3b'
down_revision: Union[str, None] = 'aad06a393a3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'potions',
        sa.Column("id", sa.Integer, primary_key=True, server_default="0"),
        sa.Column("red_ml", sa.Integer, nullable=False, server_default="0"),
        sa.Column("green_ml", sa.Integer, nullable=False, server_default="0"),
        sa.Column("blue_ml", sa.Integer, nullable=False, server_default="0"),
        sa.Column("dark_ml", sa.Integer, nullable=False, server_default="0"),
        sa.Column("quantity", sa.Integer, nullable=False, server_default="0"),
        sa.Column("price", sa.Integer, nullable=False, server_default="50"),  
        sa.Column("name", sa.String(50), nullable=False), 
        sa.Column("sku", sa.String(20), unique=True, nullable=False), 
        sa.Column("created_at", sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column("updated_at", sa.DateTime, onupdate=sa.text('CURRENT_TIMESTAMP')),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.CheckConstraint("red_ml >= 0", name="check_red_positive"),
        sa.CheckConstraint("green_ml >= 0", name="check_green_positive"),
        sa.CheckConstraint("blue_ml >= 0", name="check_blue_positive"),
        sa.CheckConstraint("dark_ml >= 0", name="check_dark_positive"),
        sa.CheckConstraint("quantity >= 0", name="check_quantity_positive"),
        sa.CheckConstraint("red_ml + green_ml + blue_ml + dark_ml = 100", name="check_total_ml"),
    )


def downgrade() -> None:
    op.drop_table('potions')