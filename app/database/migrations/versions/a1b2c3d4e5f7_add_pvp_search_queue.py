"""add pvp_search_queue table

Revision ID: a1b2c3d4e5f7
Revises: a1b2c3d4e5f6
Create Date: 2024-04-04 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Проверяем, существует ли уже таблица
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if not inspector.has_table('pvp_search_queue'):
        # Создаем таблицу pvp_search_queue
        op.create_table('pvp_search_queue',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('user_id', sa.BigInteger(), nullable=False),
            sa.Column('deck_value', sa.Integer(), nullable=False),
            sa.Column('joined_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id')
        )
        # Создаем индекс для ускорения поиска по user_id
        op.create_index(op.f('ix_pvp_search_queue_user_id'), 'pvp_search_queue', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_pvp_search_queue_user_id'), table_name='pvp_search_queue')
    op.drop_table('pvp_search_queue')