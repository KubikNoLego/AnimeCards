"""fix pvp_wins default

Revision ID: 35a67f845bfd
Revises: 4217ee8be0d8
Create Date: 2026-04-05 10:29:24.135775

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '35a67f845bfd'
down_revision: Union[str, Sequence[str], None] = '4217ee8be0d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
