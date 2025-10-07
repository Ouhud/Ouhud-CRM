# app/segments.py
import os
from datetime import datetime
from fastapi import (
    APIRouter,
    Request,
    Depends,
    Form
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Segment
from app.auth import require_login

# 📌 Router-Konfiguration
router = APIRouter(prefix="/dashboard/segments", tags=["Segments"])

# 📌 Templates-Verzeichnis
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


# ─────────────────────────────
# 📋 Liste mit Suche, Filter & Pagination
# ─────────────────────────────
@router.get("/", response_class=HTMLResponse)
def list_segments(request: Request, db: Session = Depends(get_db)):
    """Zeigt Segmentliste mit Filter-, Such- und Paginierungsoptionen an."""
    user = require_login(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    # 🔍 Such- & Filterparameter
    q = request.query_params.get("q", "").strip()
    filter_cat = request.query_params.get("filter", "").strip()
    page = max(1, int(request.query_params.get("page", 1)))
    per_page = 10

    query = db.query(Segment)

    # 🔍 Suche
    if q:
        query = query.filter(Segment.name.ilike(f"%{q}%"))

    # 🧭 Kategorie-Filter (wenn Spalte category existiert)
    if filter_cat:
        query = query.filter(Segment.category == filter_cat)

    # 📄 Pagination
    total = query.count()
    segments = (
        query.order_by(Segment.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    total_pages = (total + per_page - 1) // per_page

    # 📊 Statistik (Beispielwerte — später dynamisch)
    for s in segments:
        s.stats_count = 120  # z.B. Anzahl Kontakte
        s.stats_rate = 37.5  # z.B. Klickrate %

    return templates.TemplateResponse(
        "dashboard/segments.html",
        {
            "request": request,
            "segments": segments,
            "page": page,
            "total_pages": total_pages,
            "q": q,
            "filter": filter_cat,
            "user": user
        }
    )


# ─────────────────────────────
# ➕ Neues Segment erstellen
# ─────────────────────────────
@router.post("/create")
def create_segment(
    name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db)
):
    """Erstellt ein neues Segment."""
    new_segment = Segment(
        name=name,
        description=description,
        created_at=datetime.utcnow()
    )
    db.add(new_segment)
    db.commit()
    return RedirectResponse(url="/dashboard/segments", status_code=303)


# ─────────────────────────────
# ✏️ Segment bearbeiten – Formular
# ─────────────────────────────
@router.get("/edit/{segment_id}", response_class=HTMLResponse)
def edit_segment_page(segment_id: int, request: Request, db: Session = Depends(get_db)):
    """Zeigt die Bearbeitungsseite für ein Segment an."""
    user = require_login(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    segment = db.query(Segment).filter(Segment.id == segment_id).first()
    if not segment:
        return RedirectResponse(url="/dashboard/segments")

    return templates.TemplateResponse(
        "dashboard/segments_edit.html",
        {"request": request, "segment": segment, "user": user}
    )


# ─────────────────────────────
# 💾 Segment bearbeiten – Speichern
# ─────────────────────────────
@router.post("/edit/{segment_id}")
def edit_segment(
    segment_id: int,
    name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db)
):
    """Speichert Änderungen an einem Segment."""
    segment = db.query(Segment).filter(Segment.id == segment_id).first()
    if segment:
        segment.name = name
        segment.description = description
        segment.updated_at = datetime.utcnow()
        db.commit()
    return RedirectResponse(url="/dashboard/segments", status_code=303)


# ─────────────────────────────
# 🗑 Segment löschen
# ─────────────────────────────
@router.post("/delete")
def delete_segment(id: int = Form(...), db: Session = Depends(get_db)):
    """Löscht ein Segment."""
    segment = db.query(Segment).filter(Segment.id == id).first()
    if segment:
        db.delete(segment)
        db.commit()
    return RedirectResponse(url="/dashboard/segments", status_code=303)