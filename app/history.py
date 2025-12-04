# app/history.py
import os
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.auth import require_login
from app.models import ActivityLog

# 📌 Router für Verlauf & Aktivitäten
router = APIRouter(prefix="/dashboard", tags=["Verlauf & Aktivitäten"])

# 📁 Template-Verzeichnis ermitteln
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


# 🧰 DB Dependency (lokal, damit unabhängig von anderen Modulen)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 📜 Verlauf & Aktivitäten – Hauptseite
@router.get("/history", response_class=HTMLResponse)
def history_page(request: Request, db: Session = Depends(get_db)):
    """
    Zeigt die letzten Benutzer- und Systemaktivitäten im CRM an.
    Nur für eingeloggte Benutzer zugänglich.
    """
    user = request.state.user
    if not user:
        # Redirect zur Login-Seite, wenn nicht eingeloggt
        return RedirectResponse(url="/auth/login", status_code=303)

    # Letzte 100 Aktivitäten laden, absteigend nach Zeit
    logs = (
        db.query(ActivityLog)
        .order_by(ActivityLog.timestamp.desc())
        .limit(100)
        .all()
    )

    return templates.TemplateResponse(
        "dashboard/history.html",
        {
            "request": request,
            "user": user,
            "logs": logs
        }
    )


# 📝 Hilfsfunktion: Aktivität ins Log schreiben
def log_activity(
    db: Session,
    user_id: int = None,
    category: str = None,
    action: str = "",
    details: str = ""
):
    """
    Fügt einen neuen Eintrag ins Aktivitätslog ein.
    Diese Funktion kannst du überall im Code verwenden (z. B. bei Login, Lead-Erstellung usw.)
    """
    entry = ActivityLog(
        user_id=user_id,
        category=category,
        action=action,
        details=details
    )
    db.add(entry)
    db.commit()