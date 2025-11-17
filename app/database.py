# app/database.py (PRO Edition)

import os
import time
import urllib.parse
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError

# 🔄 .env laden
load_dotenv()

# ────────────────────────────────────────────────
# 🌍 Environment (DEV / PROD)
# ────────────────────────────────────────────────
ENV = os.getenv("ENV", "development").lower()  # development / production
IS_DEV = ENV == "development"


# ────────────────────────────────────────────────
# 🧭 DB-Typ automatisch erkennen (MySQL/Postgres)
# ────────────────────────────────────────────────
DB_TYPE = os.getenv("DB_TYPE", "mysql")  # mysql oder postgres

MYSQL_USER = os.getenv("MYSQL_USER", "")
MYSQL_PASSWORD = urllib.parse.quote_plus(os.getenv("MYSQL_PASSWORD", ""))
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DB = os.getenv("MYSQL_DB", "")

POSTGRES_USER = os.getenv("POSTGRES_USER", "")
POSTGRES_PASSWORD = urllib.parse.quote_plus(os.getenv("POSTGRES_PASSWORD", ""))
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "")


# ────────────────────────────────────────────────
# 🔐 DATABASE URL BUILDER
# ────────────────────────────────────────────────
def build_database_url() -> str:
    """Erstellt automatisch die Database-URL anhand des DB_TYPE."""
    
    if DB_TYPE == "postgres":
        return (
            f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
            f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
        )

    # default → mysql
    return (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
        f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
    )


DATABASE_URL = build_database_url()


# ────────────────────────────────────────────────
# 🔁 Auto-Reconnect (Retry System)
# ────────────────────────────────────────────────
def create_engine_with_retry(url: str, retries: int = 10, delay: int = 3):
    """Versucht wiederholt, eine DB-Verbindung aufzubauen."""
    attempt = 1
    while attempt <= retries:
        try:
            print(f"[DB] Verbindung Versuch {attempt}/{retries} → {url}")
            engine = create_engine(
                url,
                echo=IS_DEV,
                pool_pre_ping=True,    # erkennt tote Verbindungen
                pool_recycle=1800,     # recycelt alle 30 Minuten
                pool_size=10,
                max_overflow=20,
                future=True,
            )
            # Testverbindung
            with engine.connect() as conn:
                print("[DB] Verbindung erfolgreich! 🚀")
            return engine

        except OperationalError as e:
            print(f"[DB] Fehler: {e}")
            print(f"[DB] Neuer Versuch in {delay} Sekunden...")
            time.sleep(delay)
            attempt += 1

    raise RuntimeError("❌ DB konnte nicht verbunden werden — bitte prüfen!")


# Engine mit Auto-Reconnect
engine = create_engine_with_retry(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ────────────────────────────────────────────────
# 📌 Dependency für FastAPI (DB Session)
# ────────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ────────────────────────────────────────────────
# 🧱 Alembic Migrations Support
# ────────────────────────────────────────────────
def init_db():
    """
    Nur zum allerersten Start (oder wenn man bewusst kein Alembic nutzt).
    """
    import app.models
    Base.metadata.create_all(bind=engine)
    print("📦 Datenbanktabellen erstellt (ohne Alembic)")