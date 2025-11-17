"""Add conditions_json to workflow_triggers

Revision ID: 9220fcfbe76e
Revises: 4629324b2252
Create Date: 2025-11-15 22:33:27.103550
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers
revision: str = '9220fcfbe76e'
down_revision: Union[str, Sequence[str], None] = '4629324b2252'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)

    columns = [col['name'] for col in inspector.get_columns('workflow_triggers')]

    # Nur wenn Spalte NICHT existiert
    if "conditions_json" not in columns:
        op.add_column(
            "workflow_triggers",
            sa.Column("conditions_json", sa.Text(), nullable=True)
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)

    columns = [col['name'] for col in inspector.get_columns('workflow_triggers')]

    # Nur löschen, wenn Spalte existiert
    if "conditions_json" in columns:
        op.drop_column("workflow_triggers", "conditions_json")