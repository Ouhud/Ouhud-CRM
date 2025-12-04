# app/forms.py
import os
import json
from datetime import datetime
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Form as FormModel
from app.auth import require_login

router = APIRouter(prefix="/dashboard/forms", tags=["Forms"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


# 📋 Formular-Liste mit Suche & Pagination
@router.get("/", response_class=HTMLResponse)
def list_forms(request: Request, db: Session = Depends(get_db)):
    user = request.state.user
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    q = request.query_params.get("q", "").strip()
    page = int(request.query_params.get("page", 1))
    per_page = 10

    query = db.query(FormModel)
    if q:
        query = query.filter(FormModel.name.ilike(f"%{q}%"))

    total = query.count()
    forms = (
        query.order_by(FormModel.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    total_pages = (total + per_page - 1) // per_page

    return templates.TemplateResponse(
        "dashboard/forms.html",
        {
            "request": request,
            "forms": forms,
            "q": q,
            "page": page,
            "total_pages": total_pages,
            "user": user,
        }
    )


# ➕ Neues Formular erstellen
@router.post("/create")
def create_form(
    name: str = Form(...),
    description: str = Form(""),
    form_type: str = Form("custom"),
    db: Session = Depends(get_db)
):
    new_form = FormModel(
        name=name,
        description=description,
        form_type=form_type,
        created_at=datetime.utcnow()
    )
    db.add(new_form)
    db.commit()
    return RedirectResponse(url="/dashboard/forms", status_code=303)


# ✏️ Formular bearbeiten (GET)
@router.get("/edit/{form_id}", response_class=HTMLResponse)
def edit_form_page(form_id: int, request: Request, db: Session = Depends(get_db)):
    form = db.query(FormModel).filter(FormModel.id == form_id).first()
    if not form:
        return RedirectResponse(url="/dashboard/forms")
    return templates.TemplateResponse(
        "dashboard/forms_edit.html",
        {"request": request, "form": form}
    )


# ✏️ Formular bearbeiten (POST)
@router.post("/edit/{form_id}")
def edit_form(
    form_id: int,
    name: str = Form(...),
    description: str = Form(""),
    form_type: str = Form("custom"),
    db: Session = Depends(get_db)
):
    form = db.query(FormModel).filter(FormModel.id == form_id).first()
    if form:
        form.name = name
        form.description = description
        form.form_type = form_type
        form.updated_at = datetime.utcnow()
        db.commit()
    return RedirectResponse(url="/dashboard/forms", status_code=303)


# 🗑 Formular löschen
@router.post("/delete")
def delete_form(id: int = Form(...), db: Session = Depends(get_db)):
    form = db.query(FormModel).filter(FormModel.id == id).first()
    if form:
        db.delete(form)
        db.commit()
    return RedirectResponse(url="/dashboard/forms", status_code=303)