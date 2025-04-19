"""migrate potions to potions table



Revision ID: 94f7736daffe
Revises: b4b336f23567
Create Date: 2025-04-19 15:26:45.731521

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '94f7736daffe'
down_revision: Union[str, None] = 'b4b336f23567'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:    
    op.create_table(
        'potions',
        sa.Column("id", sa.Integer, primary_key=True),
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
        
    op.execute(
        """
        INSERT INTO potions (sku, name, quantity, red_ml, green_ml, blue_ml, dark_ml)
        SELECT 
            'RED_POTIONS_0' as sku,
            'red potion' as name,
            red_potions as quantity,
            100 as red_ml,
            0 as green_ml,
            0 as blue_ml,
            0 as dark_ml
        FROM global_inventory
        WHERE red_potions > 0;

        INSERT INTO potions (sku, name, quantity, red_ml, green_ml, blue_ml, dark_ml)
        SELECT 
            'GREEN_POTIONS_0' as sku,
            'green potion' as name,
            green_potions as quantity,
            0 as red_ml,
            100 as green_ml,
            0 as blue_ml,
            0 as dark_ml
        FROM global_inventory
        WHERE green_potions > 0;

        INSERT INTO potions (sku, name, quantity, red_ml, green_ml, blue_ml, dark_ml)
        SELECT 
            'BLUE_POTIONS_0' as sku,
            'blue potion' as name,
            blue_potions as quantity,
            0 as red_ml,
            0 as green_ml,
            100 as blue_ml,
            0 as dark_ml
        FROM global_inventory
        WHERE blue_potions > 0;

        UPDATE global_inventory SET
            red_potions = 0,
            green_potions = 0,
            blue_potions = 0;
        """
    )

    op.drop_column('global_inventory', 'red_potions')
    op.drop_column('global_inventory', 'green_potions')
    op.drop_column('global_inventory', 'blue_potions')


def downgrade() -> None:
    op.add_column('global_inventory', sa.Column('red_potions', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('global_inventory', sa.Column('green_potions', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('global_inventory', sa.Column('blue_potions', sa.Integer(), nullable=False, server_default='0'))

    op.execute(
        """
        UPDATE global_inventory SET
            red_potions = COALESCE((SELECT quantity FROM potions WHERE sku = 'RED_POTIONS_0'), 0),
            green_potions = COALESCE((SELECT quantity FROM potions WHERE sku = 'GREEN_POTIONS_0'), 0),
            blue_potions = COALESCE((SELECT quantity FROM potions WHERE sku = 'BLUE_POTIONS_0'), 0)
        """
    )
