"""add card_type column

Revision ID: add_card_type
Revises:
Create Date: 2024-06-02 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_card_type'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # First, drop the existing enum type if it exists with wrong values
    op.execute("DROP TYPE IF EXISTS card_type_enum CASCADE")

    # Create the new enum type with correct values
    op.execute("CREATE TYPE card_type_enum AS ENUM ('Стандартная', 'Сезонная')")

def downgrade() -> None:
    op.execute("DROP TYPE card_type_enum")