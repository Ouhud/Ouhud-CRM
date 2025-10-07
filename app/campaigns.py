# app/campaigns.py
import os
from datetime import datetime
from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional

from app.database import get_db
from app.models import Campaign
from app.auth import require_login

router = APIRouter(prefix="/dashboard/campaigns", tags=["Campaigns"])

# 📌 Templates-Verzeichnis
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


# 📄 Kampagnen-Übersicht mit Filter + Suche
@router.get("/", response_class=HTMLResponse)
def list_campaigns(
    request: Request,
    q: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Zeigt die Liste aller Kampagnen, mit Filter- und Suchoptionen."""
    user = require_login(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    query = db.query(Campaign)

    # 🔍 Suche nach Name oder Beschreibung
    if q:
        search = f"%{q}%"
        query = query.filter(or_(Campaign.name.ilike(search), Campaign.description.ilike(search)))

    # 🧭 Filter nach Status
    if status:
        query = query.filter(Campaign.status == status)

    campaigns = query.order_by(Campaign.created_at.desc()).all()

    # 📊 Dummy-Statistiken pro Kampagne (optional, später per DB ersetzen)
    for c in campaigns:
        c.stats = {
            "recipients": 150,       # Empfängerzahl
            "sent": 120,             # Gesendete Nachrichten
            "open_rate": 64          # Öffnungsrate in %
        }

    return templates.TemplateResponse(
        "dashboard/campaigns.html",
        {
            "request": request,
            "user": user,
            "campaigns": campaigns
        }
    )


# ➕ Neue Kampagne erstellen
@router.post("/create")
def create_campaign(
    name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db)
):
    """Erstellt eine neue Kampagne im Status 'geplant'."""
    new = Campaign(
        name=name,
        description=description,
        status="geplant",
        created_at=datetime.utcnow()
    )
    db.add(new)
    db.commit()
    return RedirectResponse(url="/dashboard/campaigns", status_code=303)


# ✏️ Kampagnenstatus aktualisieren
@router.post("/update_status")
def update_campaign_status(
    id: int = Form(...),
    status: str = Form(...),
    db: Session = Depends(get_db)
):
    """Ändert den Status einer Kampagne (aktiv / abgeschlossen / geplant)."""
    campaign = db.query(Campaign).filter(Campaign.id == id).first()
    if campaign:
        campaign.status = status
        db.commit()
    return RedirectResponse(url="/dashboard/campaigns", status_code=303)


# 🗑 Kampagne löschen
@router.post("/delete")
def delete_campaign(id: int = Form(...), db: Session = Depends(get_db)):
    """Löscht eine Kampagne endgültig."""
    campaign = db.query(Campaign).filter(Campaign.id == id).first()
    if campaign:
        db.delete(campaign)
        db.commit()
    return RedirectResponse(url="/dashboard/campaigns", status_code=303)


# 📊 API: Kampagnen-Statistik (Beispiel)
@router.get("/stats/{campaign_id}")
def campaign_stats(campaign_id: int, db: Session = Depends(get_db)):
    """Gibt einfache Statistikdaten als JSON zurück (z. B. für Diagramme)."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        return JSONResponse({"error": "Kampagne nicht gefunden"}, status_code=404)

    # Beispielhafte statische Daten — hier kannst du später echte Metriken einfügen
    stats = {
        "recipients": 150,
        "sent": 120,
        "open_rate": 64,
        "click_rate": 28,
        "unsubscribed": 5
    }
    return JSONResponse(stats)