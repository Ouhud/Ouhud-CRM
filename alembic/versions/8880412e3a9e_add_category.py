"""add category

Revision ID: 8880412e3a9e
Revises: 4355377394c9
Create Date: 2025-12-05 12:20:10.582223
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '8880412e3a9e'
down_revision: Union[str, Sequence[str], None] = '4355377394c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # ❗ Kategorie-Tabelle NICHT neu erstellen (existiert bereits!)

    # 1️⃣ category_id in products hinzufügen
    op.add_column(
        'products',
        sa.Column('category_id', sa.Integer(), nullable=True)
    )

    # 2️⃣ Foreign Key setzen
    op.create_foreign_key(
        'fk_products_category',
        'products',       # von-table
        'categories',     # referenz-table
        ['category_id'],  # Spalte in products
        ['id'],           # Spalte in categories
        ondelete="SET NULL"
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_constraint('fk_products_category', 'products', type_='foreignkey')
    op.drop_column('products', 'category_id')