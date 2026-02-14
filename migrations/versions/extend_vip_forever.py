"""Extend VIP to forever

Revision ID: extend_vip_forever
Revises: ad8dc7f15876
Create Date: 2026-02-13 18:00:00.000000

"""
from typing import Sequence, Union
from datetime import datetime, timedelta, timezone

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'extend_vip_forever'
down_revision: Union[str, Sequence[str], None] = 'ad8dc7f15876'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - extend all existing VIP subscriptions to 100 years."""
    # Создаем таймзону для Москвы (UTC+3)
    msk_timezone = timezone(timedelta(hours=3))
    
    # Вычисляем новую дату окончания - 100 лет от текущего момента
    now = datetime.now(msk_timezone)
    new_end_date = now + timedelta(days=36500)
    
    # Обновляем все существующие VIP подписки
    op.execute(
        f"UPDATE vip_subscriptions SET end_date = '{new_end_date.isoformat()}' WHERE end_date > '{now.isoformat()}'"
    )


def downgrade() -> None:
    """Downgrade schema."""
    # При откате ничего не делаем - нельзя восстановить старые даты
    pass
