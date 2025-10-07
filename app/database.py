# app/database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os
import urllib.parse

# 🌿 .env-Datei laden
load_dotenv()

# 🔐 Zugangsdaten aus Umgebungsvariablen
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = urllib.parse.quote_plus(os.getenv("MYSQL_PASSWORD"))  # Sonderzeichen sichern
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = os.getenv("MYSQL_PORT")
MYSQL_DB = os.getenv("MYSQL_DB")

# 🧭 SQLAlchemy URL
DATABASE_URL = f"mysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"

# 🧱 Engine & Session
engine = create_engine(DATABASE_URL, echo=True, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ⚡ Session Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 📌 Wichtig: Tabellen beim Start anlegen
def init_db():
    import app.models  # ⬅️ lädt alle Model-Klassen
    Base.metadata.create_all(bind=engine)