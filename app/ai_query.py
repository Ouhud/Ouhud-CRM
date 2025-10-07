# app/ai_query.py
import openai
from fastapi import (
    APIRouter, Depends, Request, Form, HTTPException
)
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AISettings, AIChatMessage, User
from app.auth import require_login, get_current_user

router = APIRouter(prefix="/dashboard/ai", tags=["AI Assistent"])
templates = Jinja2Templates(directory="templates")


# 🧠 KI-Abfrage — POST (Chat)
@router.post("/query")
@require_login
async def ai_query(
    request: Request,
    message: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Nimmt eine Benutzernachricht entgegen, liest KI-Einstellungen aus der DB,
    ruft OpenAI API auf und speichert den Verlauf.
    """
    try:
        # 1️⃣ KI-Einstellungen abrufen
        settings = db.query(AISettings).first()
        if not settings or not settings.active or not settings.api_key:
            return JSONResponse(
                {"error": "⚠️ KI ist nicht konfiguriert oder deaktiviert."},
                status_code=400
            )

        # 2️⃣ OpenAI API-Key setzen
        openai.api_key = settings.api_key

        # 3️⃣ Nutzer-Nachricht in DB speichern
        user_msg = AIChatMessage(
            user_id=user.id if user else None,
            role="user",
            content=message
        )
        db.add(user_msg)
        db.commit()

        # 4️⃣ KI-Antwort generieren
        completion = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": f"Du bist ein hilfreicher Assistent namens {settings.assistant_name}."
                },
                {"role": "user", "content": message}
            ],
        )

        reply = completion.choices[0].message["content"]

        # 5️⃣ Antwort speichern
        bot_msg = AIChatMessage(
            user_id=user.id if user else None,
            role="assistant",
            content=reply
        )
        db.add(bot_msg)
        db.commit()

        # 6️⃣ Antwort zurückgeben
        return JSONResponse({"reply": reply})

    except Exception as e:
        return JSONResponse(
            {"error": f"⚠️ Fehler beim KI-Aufruf: {str(e)}"},
            status_code=500
        )


# 🟦 KI-Frontend — GET (Chat UI)
@router.get("/assistant", response_class=HTMLResponse)
def assistant_ui(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Zeigt die Chat-Oberfläche für den KI-Assistenten an.
    Admins sehen zusätzlich den ⚙️ Einstellungs-Button.
    """
    # 👤 Login-Prüfung
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    # 🧭 KI-Konfigurationsstatus abrufen (DB)
    settings = db.query(AISettings).first()
    error = None
    if not settings or not settings.api_key or not settings.active:
        error = "⚠️ KI ist nicht konfiguriert. Bitte API-Key in den Einstellungen eintragen."

    # 👑 Admin-Erkennung
    is_admin = bool(user.role and user.role.name == "admin")

    return templates.TemplateResponse(request, "dashboard/ai_assistant.html", {
        "request": request,
        "is_admin": is_admin,
        "error": error
    })