"""merge heads

Revision ID: c66d2349a83d
Revises: ad2b11fdd81a, add_card_type
Create Date: 2026-06-16 14:18:01.205422

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c66d2349a83d'
down_revision: Union[str, Sequence[str], None] = ('ad2b11fdd81a', 'add_card_type')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
