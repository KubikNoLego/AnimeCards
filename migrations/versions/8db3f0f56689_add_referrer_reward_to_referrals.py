"""add_referrer_reward_to_referrals

Revision ID: 8db3f0f56689
Revises: 26b208238ceb
Create Date: 2026-02-08 11:18:03.028870

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8db3f0f56689'
down_revision: Union[str, Sequence[str], None] = '26b208238ceb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('referrals', sa.Column('referrer_reward', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('referrals', 'referrer_reward')
