"""fix_usercards_sequence

Revision ID: e9832b05185a
Revises: fix_varchar_length
Create Date: 2026-04-01 23:56:12.354132

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e9832b05185a'
down_revision: Union[str, Sequence[str], None] = 'fix_varchar_length'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Проверяем существование последовательности перед установкой
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    # Получаем список последовательностей (get_sequence_names возвращает список строк)
    sequences = inspector.get_sequence_names()
    
    if 'usercards_id_seq' in sequences:
        # Устанавливаем последовательность usercards_id_seq в значение, 
        # которое больше максимального id в таблице usercards
        # Это предотвращает конфликты дублирования первичного ключа
        op.execute("""
            SELECT setval('usercards_id_seq', (SELECT COALESCE(MAX(id), 0) FROM usercards) + 1, false)
        """)


def downgrade() -> None:
    """Downgrade schema."""
    # В downgrade нет необходимости что-то менять, 
    # так как установка последовательности не является деструктивной операцией
    pass