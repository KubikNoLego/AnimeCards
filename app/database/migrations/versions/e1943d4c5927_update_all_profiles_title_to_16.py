"""update_all_profiles_title_to_16

Revision ID: e1943d4c5927
Revises: 4e7fa755f4f8
Create Date: 2026-05-16 11:45:46.351140

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e1943d4c5927'
down_revision: Union[str, Sequence[str], None] = '4e7fa755f4f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    # Обновляем все профили, устанавливая title_id = 16
    op.execute("UPDATE profiles SET title_id = 16 WHERE title_id IS NULL OR title_id != 16")

def downgrade() -> None:
    """Downgrade schema."""
    # Откатываем изменения - возвращаем title_id к NULL для всех профилей
    op.execute("UPDATE profiles SET title_id = NULL WHERE title_id = 16")