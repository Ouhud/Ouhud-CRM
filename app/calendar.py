# app/calendar.py
import os
from datetime import datetime
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CalendarEvent
from app.auth import require_login

# 📁 Templates-Pfad
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# 📅 Kalender-Router
router = APIRouter(prefix="/dashboard/calendar", tags=["Calendar"])

# ─────────────────────────────
# 📄 Kalender-Seite anzeigen
# ─────────────────────────────
@router.get("/", response_class=HTMLResponse)
def calendar_page(request: Request, db: Session = Depends(get_db)):
    """
    📅 Kalender- und Aufgabenübersicht anzeigen.
    """
    user = require_login(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    return templates.TemplateResponse(
        "dashboard/calendar.html",
        {"request": request, "user": user}
    )

# ─────────────────────────────
# 📅 Events abrufen (FullCalendar API)
# ─────────────────────────────
@router.get("/events")
def get_events(db: Session = Depends(get_db)):
    """
    Gibt alle Kalender-Events als JSON zurück (für FullCalendar).
    """
    events = db.query(CalendarEvent).all()
    return [
        {
            "id": e.id,
            "title": e.title,
            "start": e.start.isoformat(),
            "end": e.end.isoformat() if e.end else None,
        }
        for e in events
    ]

# ─────────────────────────────
# ➕ Neues Event erstellen
# ─────────────────────────────
@router.post("/events")
async def create_event(data: dict, db: Session = Depends(get_db)):
    """
    Erstellt ein neues Kalender-Event aus FullCalendar-POST.
    """
    if not data.get("title") or not data.get("start"):
        raise HTTPException(status_code=400, detail="Titel und Startdatum sind erforderlich.")

    event = CalendarEvent(
        title=data["title"],
        start=datetime.fromisoformat(data["start"]),
        end=datetime.fromisoformat(data["end"]) if data.get("end") else None
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return {"status": "created", "id": event.id}

# ─────────────────────────────
# ✏️ Event aktualisieren (Drag & Drop)
# ─────────────────────────────
@router.put("/events/{event_id}")
async def update_event(event_id: int, data: dict, db: Session = Depends(get_db)):
    """
    Aktualisiert Start-/Endzeit eines Events (z.B. nach Drag & Drop im Kalender).
    """
    event = db.query(CalendarEvent).get(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event nicht gefunden")

    if data.get("start"):
        event.start = datetime.fromisoformat(data["start"])
    if data.get("end"):
        event.end = datetime.fromisoformat(data["end"])

    db.commit()
    return {"status": "updated"}

# ─────────────────────────────
# 🗑 Event löschen
# ─────────────────────────────
@router.delete("/events/{event_id}")
async def delete_event(event_id: int, db: Session = Depends(get_db)):
    """
    Löscht ein Kalender-Event anhand seiner ID.
    """
    event = db.query(CalendarEvent).get(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event nicht gefunden")

    db.delete(event)
    db.commit()
    return {"status": "deleted"}