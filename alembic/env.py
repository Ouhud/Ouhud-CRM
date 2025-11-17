from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
from urllib.parse import quote_plus

# ------------------------------
# IMPORT MODELS + BASE
# ------------------------------
from app.database import Base
import app.models  # noqa: F401

# Alembic config
config = context.config

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ------------------------------
# BUILD DATABASE URL YOURSELF
# ------------------------------
MYSQL_USER = os.getenv("MYSQL_USER", "crm_user")
MYSQL_PASS = os.getenv("MYSQL_PASSWORD", "Gloria28082022@")
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DB   = os.getenv("MYSQL_DB", "crm")

ENCODED_PASS = quote_plus(MYSQL_PASS)

DATABASE_URL = (
    f"mysql+pymysql://{MYSQL_USER}:{ENCODED_PASS}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
)

# IMPORTANT: DO NOT write URL into alembic.ini
# config.set_main_option("sqlalchemy.url", DATABASE_URL)  # ❌ Remove this!


target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in offline mode."""

    context.configure(
        url=DATABASE_URL,   # ← Set URL here directly
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in online mode."""

    # Read config normally
    cfg_section = config.get_section(config.config_ini_section) or {}

    # Inject URL directly here — NOT into the config object
    cfg_section["sqlalchemy.url"] = DATABASE_URL

    connectable = engine_from_config(
        cfg_section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
    
    