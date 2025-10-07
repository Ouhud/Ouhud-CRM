# app/leads.py
import os
from datetime import datetime
from fastapi import (
    APIRouter,
    Request,
    Depends,
    Form,
    HTTPException,
    status
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.database import get_db
from app.auth import require_login
from app.models import LeadDB, LeadStatus

# 📂 Templates-Verzeichnis
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# 🌐 Router
router = APIRouter(prefix="/dashboard", tags=["Leads & Opportunities"])


# ============================================================
# 📄 1) Leads-Übersicht
# ============================================================
@router.get("/leads", response_class=HTMLResponse)
def leads_page(
    request: Request,
    db: Session = Depends(get_db),
    success: str = None,
    error: str = None
):
    """
    Zeigt die Übersicht aller Leads (Opportunities) an.
    """
    user = require_login(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    leads = db.query(LeadDB).order_by(LeadDB.created_at.desc()).all()

    return templates.TemplateResponse(
        "dashboard/leads.html",
        {
            "request": request,
            "user": user,
            "leads": leads,
            "LeadStatus": LeadStatus,
            "success": success,
            "error": error,
        }
    )


# ============================================================
# ➕ 2) Lead erstellen
# ============================================================
@router.post("/leads/create")
def create_lead(
    request: Request,
    name: str = Form(...),
    email: str = Form(None),
    phone: str = Form(None),
    company: str = Form(None),
    status: str = Form("Neu"),
    db: Session = Depends(get_db)
):
    """
    Erstellt einen neuen Lead-Eintrag (Interessent).
    """
    user = require_login(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    if not name.strip():
        return RedirectResponse(
            url="/dashboard/leads?error=Name%20ist%20erforderlich",
            status_code=303
        )

    try:
        lead = LeadDB(
            name=name.strip(),
            email=email.strip() if email else None,
            phone=phone.strip() if phone else None,
            company=company.strip() if company else None,
            status=status
        )
        db.add(lead)
        db.commit()
        return RedirectResponse(
            url="/dashboard/leads?success=Lead%20wurde%20erstellt",
            status_code=303
        )
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Fehler beim Speichern des Leads")


# ============================================================
# 🗑 3) Lead löschen
# ============================================================
@router.post("/leads/{lead_id}/delete")
def delete_lead(
    lead_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Löscht einen Lead unwiderruflich.
    """
    user = require_login(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    lead = db.query(LeadDB).filter(LeadDB.id == lead_id).first()
    if not lead:
        return RedirectResponse(
            url="/dashboard/leads?error=Lead%20nicht%20gefunden",
            status_code=303
        )

    try:
        db.delete(lead)
        db.commit()
        return RedirectResponse(
            url="/dashboard/leads?success=Lead%20wurde%20gelöscht",
            status_code=303
        )
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Fehler beim Löschen des Leads")
    
    
    