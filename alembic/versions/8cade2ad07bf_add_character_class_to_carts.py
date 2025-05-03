"""add character class to carts

Revision ID: 8cade2ad07bf
Revises: 21a7be5f4842
Create Date: 2025-05-02 19:46:22.667272

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8cade2ad07bf'
down_revision: Union[str, None] = '21a7be5f4842'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('carts', 
        sa.Column('character_class', sa.String, nullable=True)
    )

    op.execute("""
        UPDATE carts 
        SET character_class = 'unknown'
        WHERE character_class IS NULL
    """)

def downgrade() -> None:
    op.drop_column('carts', 'character_class')
