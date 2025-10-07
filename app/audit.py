# app/audit.py
import os
from datetime import datetime
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import AuditLog

router = APIRouter(prefix="/dashboard/audit", tags=["Audit"])

# 📌 Templates-Verzeichnis
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# 🧰 DB-Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 📄 Audit Log mit Filter & Suche
@router.get("/", response_class=HTMLResponse)
async def audit_page(request: Request, db: Session = Depends(get_db)):
    q = request.query_params.get("q", "")
    action_filter = request.query_params.get("action", "")

    query = db.query(AuditLog)

    # 🔍 Filterung nach Suchbegriff
    if q:
        query = query.filter(
            or_(
                AuditLog.user.ilike(f"%{q}%"),
                AuditLog.action.ilike(f"%{q}%"),
                AuditLog.details.ilike(f"%{q}%"),
                AuditLog.ip_address.ilike(f"%{q}%")
            )
        )

    # 📝 Filterung nach Aktionstyp
    if action_filter:
        query = query.filter(AuditLog.action == action_filter)

    logs = query.order_by(AuditLog.timestamp.desc()).limit(300).all()
    return templates.TemplateResponse(
        "audit.html", {"request": request, "logs": logs}
    )


# 📌 Hilfsfunktion: neuen Audit-Eintrag anlegen
def add_audit_log(db: Session, user: str, action: str, details: str = None, ip: str = None):
    """
    Fügt einen neuen Eintrag in die Audit-Log-Tabelle ein.
    Diese Funktion kann überall im System aufgerufen werden, z.B. bei Login, API-Änderungen usw.
    """
    entry = AuditLog(
        user=user,
        action=action,
        details=details,
        ip_address=ip,
        timestamp=datetime.utcnow()
    )
    db.add(entry)
    db.commit()


# 📌 Beispiel: Middleware / Event für automatisches Logging
# Du kannst z.B. in main.py eine Middleware setzen, die alle Requests loggt
# (Optional, je nach Datenschutz-Anforderungen)