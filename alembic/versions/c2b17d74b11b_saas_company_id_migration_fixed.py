from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import Integer, String

# revision identifiers, used by Alembic.
revision = 'c2b17d74b11b'
down_revision = 'e192d6891976'
branch_labels = None
depends_on = None


def upgrade():
    # Step 1: Ensure default company exists
    op.execute("""
        INSERT IGNORE INTO companies (id, name, subdomain, owner_email, plan, status, created_at)
        VALUES (1, 'Default Company', 'default', 'admin@localhost', 'free', 'active', NOW());
    """)

    # Helper to add a column only if missing
    def safe_add_column(table, col):
        try:
            op.add_column(table, col)
        except Exception:
            pass

    # Step 2: Add company_id columns to all tables (without FK first)
    tables = [
        "activity_logs", "ai_settings", "audit_logs", "automation_designer",
        "calendar_events", "call_logs", "campaigns", "chat_messages",
        "company_settings", "documents", "forms", "integrations",
        "invoices", "leads", "messages", "offers", "orders",
        "payment_logs", "payments", "pbx_settings", "products",
        "roles", "segments", "users", "whatsapp_messages",
        "whatsapp_settings"
    ]

    for t in tables:
        safe_add_column(t, sa.Column("company_id", sa.Integer(), nullable=True))

    # Step 3: Set all existing rows to company_id = 1
    for t in tables:
        op.execute(f"UPDATE {t} SET company_id = 1 WHERE company_id IS NULL;")

    # Step 4: Now apply NOT NULL
    for t in tables:
        try:
            op.alter_column(t, "company_id", nullable=False)
        except Exception:
            pass

    # Step 5: Now add foreign keys
    for t in tables:
        try:
            op.create_foreign_key(
                f"fk_{t}_company_id",
                t,
                "companies",
                ["company_id"],
                ["id"]
            )
        except Exception:
            pass


def downgrade():

    tables = [
        "activity_logs", "ai_settings", "audit_logs", "automation_designer",
        "calendar_events", "call_logs", "campaigns", "chat_messages",
        "company_settings", "documents", "forms", "integrations",
        "invoices", "leads", "messages", "offers", "orders",
        "payment_logs", "payments", "pbx_settings", "products",
        "roles", "segments", "users", "whatsapp_messages",
        "whatsapp_settings"
    ]

    # Remove foreign keys
    for t in tables:
        try:
            op.drop_constraint(f"fk_{t}_company_id", t, type_="foreignkey")
        except Exception:
            pass

    # Remove columns
    for t in tables:
        try:
            op.drop_column(t, "company_id")
        except Exception:
            pass