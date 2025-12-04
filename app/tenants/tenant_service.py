# app/tenants/tenant_service.py

from app.database import SessionLocal
from app.models import Company

BASE_DOMAINS = [
    "ouhud.com",
    "crm.ouhud.com",
    "localhost",
    "127.0.0.1",
]


def extract_subdomain(host: str) -> str | None:
    """
    Extrahiert Subdomain aus dem Host.
    Beispiel:
        firma.ouhud.com     → "firma"
        crm.ouhud.com       → "crm"
        ouhud.com           → None
        localhost           → None
        127.0.0.1           → None
    """

    # ⚠️ Wichtig: Port NICHT entfernen!
    # → sonst findet er die Firma nicht
    clean_host = host.lower()

    # Lokale Entwicklung
    if clean_host in ("localhost", "127.0.0.1", "127.0.0.1:8000"):
        return None

    # ngrok / cloudflare tunnel ausschließen
    if clean_host.endswith(".ngrok-free.app") or clean_host.endswith(".trycloudflare.com"):
        return None

    parts = clean_host.split(".")

    # weniger als 3 Teile → keine Subdomain
    if len(parts) < 3:
        return None

    root_domain = ".".join(parts[-2:])
    if root_domain not in BASE_DOMAINS:
        return None

    return ".".join(parts[:-2])


def resolve_company_by_subdomain(subdomain: str):
    if not subdomain:
        return None

    db = SessionLocal()
    try:
        return db.query(Company).filter(Company.subdomain == subdomain).first()
    finally:
        db.close()


def resolve_company_by_custom_domain(host: str):
    # ⚠️ WICHTIG: Port NICHT entfernen
    clean_host = host.lower()

    db = SessionLocal()
    try:
        return db.query(Company).filter(Company.custom_domain == clean_host).first()
    finally:
        db.close()


def resolve_company(identifier: str):
    if not identifier:
        return None

    tenant = resolve_company_by_custom_domain(identifier)
    if tenant:
        return tenant

    return resolve_company_by_subdomain(identifier)