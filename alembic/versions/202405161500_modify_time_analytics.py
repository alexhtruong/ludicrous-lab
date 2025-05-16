"""modify_time_analytics

Revision ID: 202405161500
Revises: 20b89b903e2f
Create Date: 2024-05-16 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '202405161500'
down_revision: Union[str, None] = '20b89b903e2f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'time_analytics_new',
        sa.Column('day_of_week', sa.String, nullable=False),
        sa.Column('hour_of_day', sa.Integer, nullable=False),
        sa.Column('total_sales', sa.Integer, nullable=False, server_default='0'),
        sa.Column('total_gold', sa.Float, nullable=False, server_default='0'),
        sa.Column('visitor_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('day_of_week', 'hour_of_day')
    )
    
    op.execute("""
        INSERT INTO time_analytics_new (
            day_of_week, hour_of_day, total_sales, total_gold, 
            visitor_count, created_at
        )
        SELECT 
            day_of_week, 
            tick_of_day,
            total_sales,
            total_gold,
            visitor_count,
            created_at
        FROM time_analytics
    """)
    
    op.drop_table('time_analytics')
    op.rename_table('time_analytics_new', 'time_analytics')


def downgrade() -> None:
    op.create_table(
        'time_analytics_old',
        sa.Column('tick_id', sa.Integer, primary_key=True),
        sa.Column('day_of_week', sa.String, nullable=False),
        sa.Column('tick_of_day', sa.Integer, nullable=False),
        sa.Column('total_sales', sa.Integer, nullable=False, server_default='0'),
        sa.Column('total_gold', sa.Float, nullable=False, server_default='0'),
        sa.Column('stock_out_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('visitor_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    
    op.execute("""
        INSERT INTO time_analytics_old (
            day_of_week, tick_of_day, total_sales, total_gold,
            stock_out_count, visitor_count, created_at
        )
        SELECT 
            day_of_week,
            hour_of_day,
            total_sales,
            total_gold,
            0 as stock_out_count,
            visitor_count,
            created_at
        FROM time_analytics
    """)
    
    op.drop_table('time_analytics')
    op.rename_table('time_analytics_old', 'time_analytics')
