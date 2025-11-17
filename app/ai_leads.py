# app/ai_leads.py
import os
import json
from typing import Any, Dict, Optional
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import require_login
from app.database import get_db
from app.models import LeadDB
from app.utils.ai_provider import AIProvider   # 🔥 UNIVERSAL PROVIDER


# ---------------------------------------------------------
# Templates
# ---------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "../templates"))


# ---------------------------------------------------------
# Router
# ---------------------------------------------------------
router = APIRouter(
    prefix="/dashboard/ai",
    tags=["AI Lead Scoring"]
)


# ---------------------------------------------------------
# Safe JSON Parsing (Pylance-frei)
# ---------------------------------------------------------
def safe_json(raw: Optional[str]) -> Dict[str, Any]:
    """
    Robust JSON parser — toleriert Fehler, Text und ungültige Formats.
    """
    if raw is None:
        return {}

    raw = raw.strip()

    # Falls OpenAI direkt gültiges JSON liefert
    if raw.startswith("{") and raw.endswith("}"):
        try:
            return json.loads(raw)
        except Exception:
            pass

    # JSON aus Mixed-Content extrahieren
    start = raw.find("{")
    end = raw.rfind("}") + 1

    if start != -1 and end != -1:
        try:
            return json.loads(raw[start:end])
        except Exception:
            return {}

    return {}


# ---------------------------------------------------------
# Leads-Übersicht
# ---------------------------------------------------------
@router.get("/leads", response_class=HTMLResponse)
def ai_leads_page(
    request: Request,
    db: Session = Depends(get_db)
):
    user = require_login(request, db)
    if not user:
        return RedirectResponse("/auth/login", 303)

    leads = db.query(LeadDB).order_by(LeadDB.created_at.desc()).all()

    return templates.TemplateResponse(
        "dashboard/ai_leads.html",
        {"request": request, "user": user, "leads": leads}
    )


# ---------------------------------------------------------
# Scoring eines einzelnen Leads
# ---------------------------------------------------------
@router.post("/leads/{lead_id}/score")
def ai_score_lead(
    lead_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    user = require_login(request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, 401)

    ai = AIProvider()  # 🌍 UNIVERSAL KI

    lead = db.query(LeadDB).filter(LeadDB.id == lead_id).first()
    if not lead:
        return JSONResponse({"error": "Lead not found"}, 404)

    # --- KI Prompt ---
    prompt = f"""
    Bewerte diesen Lead objektiv.

    GIB NUR JSON ZURÜCK:

    {{
        "score": 0-100,
        "label": "Hot" | "Warm" | "Cold",
        "reason": "kurze Begründung"
    }}

    Lead-Daten:
    Name: {lead.name}
    Email: {lead.email}
    Firma: {lead.company}
    Telefon: {lead.phone}
    """

    raw = ai.chat(prompt)
    data: Dict[str, Any] = safe_json(raw)

    # --- Werte speichern ---
    lead.score = int(data.get("score", 0))
    lead.score_label = data.get("label", "Cold")
    lead.score_reason = data.get("reason", "Keine Angabe")

    db.commit()

    return RedirectResponse(
    url=f"/dashboard/ai/leads?success=Lead%20{lead_id}%20bewertet",
    status_code=303
)


# ---------------------------------------------------------
# Scoring ALLER Leads
# ---------------------------------------------------------
@router.post("/leads/score-all")
def ai_score_all(
    request: Request,
    db: Session = Depends(get_db)
):
    user = require_login(request, db)
    if not user:
        return RedirectResponse("/auth/login", 303)

    ai = AIProvider()
    leads = db.query(LeadDB).all()

    for lead in leads:
        prompt = f"""
        Bewerte diesen Lead.

        GIB NUR JSON ZURÜCK:

        {{
            "score": 0-100,
            "label": "Hot" | "Warm" | "Cold",
            "reason": "kurze Begründung"
        }}

        Lead-Daten:
        Name: {lead.name}
        Email: {lead.email}
        Firma: {lead.company}
        """

        try:
            raw = ai.chat(prompt)
            data: Dict[str, Any] = safe_json(raw)

            lead.score = int(data.get("score", 0))
            lead.score_label = data.get("label", "Cold")
            lead.score_reason = data.get("reason", "")

        except Exception as e:
            print("AI error:", e)
            continue

    db.commit()

    return RedirectResponse("/dashboard/ai/leads?success=Scoring%20OK", 303)