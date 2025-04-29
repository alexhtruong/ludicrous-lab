"""added customers table to document purchases

Revision ID: d409de638516
Revises: 861f156fe9a0
Create Date: 2025-04-20 14:35:49.354155

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd409de638516'
down_revision: Union[str, None] = '861f156fe9a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # op.create_table(
    #     'customers',
    #     sa.Column('id', sa.Integer, primary_key=True),
    #     sa.Column('customer_name', sa.String, nullable=False)
    #     sa.Column('class', sa.String, nullable=False)
    #     sa.Column('level', sa.Integer, nullable=False)
    # )
    pass

def downgrade() -> None:
    """Downgrade schema."""
    pass
