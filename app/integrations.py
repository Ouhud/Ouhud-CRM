# app/integrations.py
import os
from datetime import datetime
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Integration
from app.auth import require_login

router = APIRouter(prefix="/dashboard/integrations", tags=["Integrationen"])

# 📌 Templates Pfad
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


# 📋 Liste mit Suche, Filter & Pagination
@router.get("/", response_class=HTMLResponse)
def list_integrations(request: Request, db: Session = Depends(get_db)):
    """Liste aller Integrationen mit Filter, Suche & Pagination"""
    user = require_login(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    # 🔍 Such- & Filterparameter
    q = request.query_params.get("q", "").strip()
    filter_type = request.query_params.get("type", "").strip()

    # 📄 Paginierung
    page = int(request.query_params.get("page", 1))
    per_page = 10

    query = db.query(Integration)
    if q:
        query = query.filter(Integration.name.ilike(f"%{q}%"))
    if filter_type:
        query = query.filter(Integration.type == filter_type)

    total = query.count()
    integrations = (
        query.order_by(Integration.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    total_pages = (total + per_page - 1) // per_page

    return templates.TemplateResponse(
        "dashboard/integrations.html",
        {
            "request": request,
            "integrations": integrations,
            "page": page,
            "total_pages": total_pages,
            "q": q,
            "filter_type": filter_type,
            "user": user,
        },
    )


# ➕ Integration erstellen
@router.post("/create")
def create_integration(
    name: str = Form(...),
    type: str = Form(...),
    api_key: str = Form(""),
    db: Session = Depends(get_db),
):
    """Neue Integration hinzufügen"""
    new = Integration(
        name=name,
        type=type,
        api_key=api_key,
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db.add(new)
    db.commit()
    return RedirectResponse(url="/dashboard/integrations", status_code=303)


# ✏️ Edit-Seite anzeigen
@router.get("/edit/{integration_id}", response_class=HTMLResponse)
def edit_integration_page(integration_id: int, request: Request, db: Session = Depends(get_db)):
    """Bearbeitungsseite für eine Integration"""
    integration = db.query(Integration).filter(Integration.id == integration_id).first()
    if not integration:
        return RedirectResponse(url="/dashboard/integrations", status_code=303)
    return templates.TemplateResponse(
        "dashboard/integrations_edit.html",
        {"request": request, "integration": integration},
    )


# ✏️ Integration speichern
@router.post("/edit/{integration_id}")
def edit_integration(
    integration_id: int,
    name: str = Form(...),
    type: str = Form(...),
    api_key: str = Form(""),
    is_active: str = Form("off"),
    db: Session = Depends(get_db),
):
    """Integration in der DB aktualisieren"""
    integration = db.query(Integration).filter(Integration.id == integration_id).first()
    if integration:
        integration.name = name
        integration.type = type
        integration.api_key = api_key
        integration.is_active = (is_active == "on")
        integration.updated_at = datetime.utcnow()
        db.commit()
    return RedirectResponse(url="/dashboard/integrations", status_code=303)


# 🗑 Integration löschen
@router.post("/delete")
def delete_integration(id: int = Form(...), db: Session = Depends(get_db)):
    """Integration löschen"""
    integration = db.query(Integration).filter(Integration.id == id).first()
    if integration:
        db.delete(integration)
        db.commit()
    return RedirectResponse(url="/dashboard/integrations", status_code=303)