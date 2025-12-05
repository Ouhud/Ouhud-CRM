# app/ai_settings.py
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AISettings, User
from app.auth import require_admin

import httpx

router = APIRouter(prefix="/dashboard/ai/settings", tags=["AI Settings"])
templates = Jinja2Templates(directory="templates")


# ---------------------------------------------------------
# Load or create settings (tenant or user)
# ---------------------------------------------------------
def load_settings(db: Session, user: User):
    settings = (
        db.query(AISettings)
        .filter(AISettings.company_id == user.company_id)
        .first()
    )

    if not settings:
        settings = AISettings(
            company_id=user.company_id,
            user_id=user.id,
            assistant_name="Ouhud KI-Assistent",
            provider="openai",
            model="gpt-4o-mini",
            api_key="",
            active=False,
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return settings


# ---------------------------------------------------------
# Settings page
# ---------------------------------------------------------
@router.get("/", response_class=HTMLResponse)
def ai_settings_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    settings = load_settings(db, user)

    PROVIDERS = {
        "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4.1"],
        "groq": ["llama3-70b", "llama3-8b"],
        "gemini": ["gemini-pro", "gemini-1.5-flash"],
    }

    return templates.TemplateResponse(
        "dashboard/ai_settings.html",
        {
            "request": request,
            "settings": settings,
            "providers": PROVIDERS,
            "user": user,
        },
    )


# ---------------------------------------------------------
# Save settings
# ---------------------------------------------------------
@router.post("/save")
def ai_settings_save(
    request: Request,
    assistant_name: str = Form(...),
    api_key: str = Form(""),
    provider: str = Form(...),
    model: str = Form(...),
    active: bool = Form(False),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    settings = load_settings(db, user)

    # validation
    if provider not in ["openai", "groq", "gemini"]:
        raise HTTPException(400, "Ungültiger Anbieter.")

    settings.assistant_name = assistant_name.strip()
    settings.api_key = api_key.strip()
    settings.provider = provider
    settings.model = model
    settings.active = active

    db.commit()

    return RedirectResponse("/dashboard/ai/settings?success=1", 303)


# ---------------------------------------------------------
# AJAX API Test
# ---------------------------------------------------------
@router.post("/test")
async def ai_test(api_key: str = Form(...), provider: str = Form(...)):
    try:
        if provider == "openai":
            url = "https://api.openai.com/v1/models"
            headers = {"Authorization": f"Bearer {api_key}"}

        elif provider == "groq":
            url = "https://api.groq.com/openai/v1/models"
            headers = {"Authorization": f"Bearer {api_key}"}

        elif provider == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1/models?key={api_key}"
            headers = {}

        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(url, headers=headers)

        if r.status_code == 200:
            return JSONResponse({"ok": True, "message": "Verbindung erfolgreich ✔"})

        return JSONResponse({"ok": False, "message": f"Fehler: {r.text}"})

    except Exception as e:
        return JSONResponse({"ok": False, "message": str(e)})