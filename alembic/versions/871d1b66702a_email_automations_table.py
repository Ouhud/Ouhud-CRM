"""email automations table

Revision ID: 871d1b66702a
Revises: 77dc522cfbb7
Create Date: 2025-11-22 00:01:25.588606

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '871d1b66702a'
down_revision: Union[str, Sequence[str], None] = '77dc522cfbb7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
