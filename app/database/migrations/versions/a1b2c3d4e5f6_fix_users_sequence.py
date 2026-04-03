"""fix_users_sequence

Revision ID: a1b2c3d4e5f6
Revises: e9832b05185a
Create Date: 2026-04-02 00:03:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'e9832b05185a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Устанавливаем последовательность users_id_seq в правильное значение
    # users.id использует BigInteger без autoincrement, но может иметь последовательность
    # если таблица пересоздавалась или импортировалась
    op.execute("""
        SELECT setval('users_id_seq', (SELECT COALESCE(MAX(id), 0) FROM users) + 1, false)
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # В downgrade нет необходимости что-то менять
    pass