"""fix ai_settings

Revision ID: 4629324b2252
Revises:
Create Date: 2025-11-15 13:24:20.155824
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = '4629324b2252'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    bind = op.get_bind()
    inspector = inspect(bind)

    # ======================================
    # SAFE FIX FOR ai_settings — prevents:
    # 1060 Duplicate column name 'user_id'
    # ======================================
    ai_cols = [c['name'] for c in inspector.get_columns('ai_settings')]

    with op.batch_alter_table('ai_settings', schema=None) as batch_op:

        # user_id hinzufügen, wenn NICHT existiert
        if 'user_id' not in ai_cols:
            batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
            batch_op.create_foreign_key(None, 'users', ['user_id'], ['id'])

        # provider hinzufügen
        if 'provider' not in ai_cols:
            batch_op.add_column(sa.Column('provider', sa.String(length=50), nullable=False))

        # model hinzufügen
        if 'model' not in ai_cols:
            batch_op.add_column(sa.Column('model', sa.String(length=100), nullable=False))

        # api_provider entfernen, wenn existiert
        if 'api_provider' in ai_cols:
            batch_op.drop_column('api_provider')

    # ======================================
    # Der Rest bleibt unverändert
    # ======================================

    with op.batch_alter_table('campaigns', schema=None) as batch_op:
        batch_op.alter_column(
            'status',
            existing_type=mysql.VARCHAR(length=20),
            type_=sa.Enum('draft', 'active', 'completed', 'archived', name='campaignstatus'),
            existing_nullable=True
        )

    with op.batch_alter_table('chat_messages', schema=None) as batch_op:
        batch_op.alter_column('timestamp', existing_type=mysql.DATETIME(), nullable=False)

    with op.batch_alter_table('company_settings', schema=None) as batch_op:
        batch_op.alter_column('company_name', existing_type=mysql.VARCHAR(length=255), nullable=True)

    with op.batch_alter_table('customers', schema=None) as batch_op:
        batch_op.alter_column('name', type_=sa.String(100), existing_nullable=False)
        batch_op.alter_column('email', type_=sa.String(120), existing_nullable=False)
        batch_op.alter_column('country', type_=sa.String(100), existing_nullable=True)
        batch_op.drop_column('updated_at')
        batch_op.drop_column('created_at')

    with op.batch_alter_table('integrations', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_integrations_id'), ['id'], unique=False)

    with op.batch_alter_table('invoice_items', schema=None) as batch_op:
        batch_op.alter_column('unit_price', type_=sa.Float(), existing_nullable=False)
        batch_op.alter_column('tax_rate', type_=sa.Float(), existing_nullable=False)

    with op.batch_alter_table('invoices', schema=None) as batch_op:
        batch_op.alter_column('status', nullable=False)

    with op.batch_alter_table('pbx_settings', schema=None) as batch_op:
        batch_op.alter_column('id', type_=sa.Integer(), autoincrement=True)
        batch_op.alter_column('api_url', type_=sa.String(255), nullable=False)
        batch_op.alter_column('api_key', type_=sa.String(255), nullable=True)
        batch_op.alter_column('sip_password', type_=sa.String(100), nullable=True)
        batch_op.alter_column('created_at', type_=sa.DateTime(), nullable=True)
        batch_op.drop_index(batch_op.f('id'))
        batch_op.create_index(batch_op.f('ix_pbx_settings_id'), ['id'])
        batch_op.drop_column('company_id')
        batch_op.drop_column('webhook_url')

    with op.batch_alter_table('segments', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_segments_id'), ['id'], unique=False)

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('email', existing_type=mysql.VARCHAR(length=100), nullable=False)
        batch_op.drop_index(batch_op.f('username'))
        batch_op.create_index(batch_op.f('ix_users_reset_token'), ['reset_token'], unique=False)
        batch_op.create_index(batch_op.f('ix_users_username'), ['username'], unique=True)
        if 'role' in [c['name'] for c in inspector.get_columns('users')]:
            batch_op.drop_column('role')


def downgrade() -> None:
    """Downgrade schema (unchanged)"""
    pass