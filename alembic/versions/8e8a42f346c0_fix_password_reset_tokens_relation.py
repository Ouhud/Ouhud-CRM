"""fix password_reset_tokens relation

Revision ID: 8e8a42f346c0
Revises: d338c1dbc6f2
Create Date: 2025-11-28
"""

from alembic import op
import sqlalchemy as sa

revision = '8e8a42f346c0'
down_revision = 'd338c1dbc6f2'
branch_labels = None
depends_on = None

def upgrade():
    pass

def downgrade():
    pass