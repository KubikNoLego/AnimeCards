"""increase varchar length for verse fields

Revision ID: fix_varchar_length
Revises: c8296f330efa
Create Date: 2026-03-23 03:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fix_varchar_length'
down_revision: Union[str, Sequence[str], None] = 'c8296f330efa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Увеличиваем длину verse_name в таблице cards с 50 до 150
    op.alter_column('cards', 'verse_name',
                    existing_type=sa.String(50),
                    type_=sa.String(150),
                    existing_nullable=False)
    
    # Увеличиваем длину name в таблице verses с 50 до 150
    op.alter_column('verses', 'name',
                    existing_type=sa.String(50),
                    type_=sa.String(150),
                    existing_nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Возвращаем длину verse_name в таблице cards с 150 до 50
    op.alter_column('cards', 'verse_name',
                    existing_type=sa.String(150),
                    type_=sa.String(50),
                    existing_nullable=False)
    
    # Возвращаем длину name в таблице verses с 150 до 50
    op.alter_column('verses', 'name',
                    existing_type=sa.String(150),
                    type_=sa.String(50),
                    existing_nullable=False)