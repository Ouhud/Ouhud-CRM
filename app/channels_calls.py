# app/channels_calls.py
import os
from datetime import datetime
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import CallLog, PBXSettings   # ⚠️ Stelle sicher, dass PBXSettings existiert!

router = APIRouter(prefix="/dashboard/calls", tags=["Calls"])

# 📁 Templates-Verzeichnis
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# 🧭 DB-Session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =========================================================
# 1️⃣ 📋 Call-Historie anzeigen
# =========================================================
@router.get("/", response_class=HTMLResponse)
async def list_calls(request: Request, db: Session = Depends(get_db)):
    calls = db.query(CallLog).order_by(CallLog.timestamp.desc()).all()
    return templates.TemplateResponse(request, "calls_list.html", {
        "request": request,
        "calls": calls
    })

# =========================================================
# 2️⃣ ➕ Dummy-Anruf hinzufügen (Test)
# =========================================================
@router.post("/add")
async def add_call(
    direction: str = Form(...),
    phone_number: str = Form(...),
    contact_name: str = Form(None),
    duration: int = Form(0),
    status: str = Form("completed"),
    db: Session = Depends(get_db)
):
    log = CallLog(
        direction=direction,
        phone_number=phone_number,
        contact_name=contact_name,
        duration=duration,
        status=status
    )
    db.add(log)
    db.commit()
    return RedirectResponse(url="/dashboard/calls", status_code=303)

# =========================================================
# 3️⃣ ⚙️ Telephony / PBX Settings
# =========================================================

@router.get("/settings", response_class=HTMLResponse)
async def get_telephony_settings(request: Request, db: Session = Depends(get_db)):
    """Zeigt die aktuelle PBX/Telephony-Konfiguration an."""
    settings = db.query(PBXSettings).first()
    return templates.TemplateResponse(request, "telephony_settings.html", {
        "request": request,
        "settings": settings
    })


@router.post("/settings/save")
async def save_telephony_settings(
    provider: str = Form(...),
    api_url: str = Form(...),
    api_key: str = Form(None),
    sip_user: str = Form(None),
    sip_password: str = Form(None),
    db: Session = Depends(get_db)
):
    """Speichert oder aktualisiert die PBX/VoIP-Einstellungen."""
    settings = db.query(PBXSettings).first()
    if settings:
        settings.provider = provider
        settings.api_url = api_url
        settings.api_key = api_key
        settings.sip_user = sip_user
        settings.sip_password = sip_password
    else:
        settings = PBXSettings(
            provider=provider,
            api_url=api_url,
            api_key=api_key,
            sip_user=sip_user,
            sip_password=sip_password
        )
        db.add(settings)
    db.commit()
    return RedirectResponse(url="/dashboard/calls/settings", status_code=303)

# =========================================================
# 4️⃣ 📡 Optional: Test-Verbindung zur PBX (z. B. FritzBox / Twilio)
# =========================================================

@router.get("/settings/test", response_class=JSONResponse)
async def test_telephony_connection(db: Session = Depends(get_db)):
    """Testet die Verbindung zur API der Telefonanlage."""
    settings = db.query(PBXSettings).first()
    if not settings:
        return JSONResponse({"success": False, "message": "Keine Einstellungen gefunden."})

    # Beispiel: Nur Dummy-Test, kann später FritzBox/Twilio API anpingen
    try:
        if "fritz" in settings.provider.lower():
            # Hier könnte man TR-064 Request testen
            return JSONResponse({"success": True, "message": "FritzBox-Einstellungen erkannt."})
        elif "twilio" in settings.provider.lower():
            return JSONResponse({"success": True, "message": "Twilio API-Token vorhanden."})
        else:
            return JSONResponse({"success": True, "message": f"Provider '{settings.provider}' gespeichert."})
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)})