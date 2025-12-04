"""create activities table

Revision ID: b7e6cf1d49c5
Revises: 871d1b66702a
Create Date: 2025-11-27 19:38:26.705680

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b7e6cf1d49c5'
down_revision: Union[str, Sequence[str], None] = '871d1b66702a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create activities table ONLY."""
    op.create_table(
        'activities',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    """Drop only activities table."""
    op.drop_table('activities')