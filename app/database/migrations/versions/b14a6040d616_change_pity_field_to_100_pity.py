"""invert pity (100 - pity)

Revision ID: invert_pity
Revises: <твой_предыдущий_revision>
Create Date: 2026-04-14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = 'b14a6040d616'
down_revision: Union[str, Sequence[str], None] = 'c8b11f3ec3a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade():
    # обновляем все значения pity
    op.execute(
        sa.text("UPDATE users SET pity = 100 - pity")
    )


def downgrade():
    # откат = та же операция (она симметричная)
    op.execute(
        sa.text("UPDATE users SET pity = 100 - pity")
    )