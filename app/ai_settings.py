# app/ai_settings.py
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AISettings, User
from app.auth import require_admin

router = APIRouter(prefix="/dashboard/ai/settings", tags=["AI Settings"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
def ai_settings_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    settings = db.query(AISettings).first()
    if not settings:
        settings = AISettings(
            assistant_name="Ouhud Assistant",
            api_provider="openai",
            active=False
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return templates.TemplateResponse(
        "dashboard/ai_settings.html",
        {
            "request": request,
            "settings": settings,
            "user": user
        }
    )


@router.post("/save")
def save_ai_settings(
    request: Request,
    assistant_name: str = Form(...),
    api_key: str = Form(...),
    api_provider: str = Form(...),
    active: bool = Form(False),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    settings = db.query(AISettings).first()
    if not settings:
        settings = AISettings()

    settings.assistant_name = assistant_name.strip()
    settings.api_key = api_key.strip()
    settings.api_provider = api_provider.strip()
    settings.active = active

    db.add(settings)
    db.commit()

    return RedirectResponse(
        url="/dashboard/ai/settings",
        status_code=303
    )