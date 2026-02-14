"""remove_email_field_from_users

Revision ID: f27044801c79
Revises: 2e68971f63ca
Create Date: 2026-01-24 20:13:56.020224

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text
from sqlalchemy.exc import ProgrammingError

# revision identifiers, used by Alembic.
revision: str = 'f27044801c79'
down_revision: Union[str, Sequence[str], None] = '2e68971f63ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    # Check if email column exists before trying to remove it
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Check if the email column exists in the users table
    if 'email' in [col['name'] for col in inspector.get_columns('users')]:
        op.drop_column('users', 'email')
        print("Email column removed from users table")
    else:
        print("Email column does not exist in users table - no action needed")

def downgrade() -> None:
    """Downgrade schema."""
    # Add email column back if it was removed
    op.add_column('users', sa.Column('email', sa.String(length=255), nullable=True))
    print("Email column added back to users table")