# app/ai_query.py

from fastapi import (
    APIRouter, Depends, Request, Form
)
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AISettings, AIChatMessage, User
from app.auth import require_login, get_current_user

from openai import OpenAI   # Neue OpenAI API

router = APIRouter(prefix="/dashboard/ai", tags=["AI Assistent"])
templates = Jinja2Templates(directory="templates")


# =========================================================
# 🧠 KI-Abfrage — POST (Chat)
# =========================================================
@router.post("/query")
@require_login
async def ai_query(
    request: Request,
    message: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Empfängt eine Nachricht, ruft KI auf, speichert Chatverlauf.
    """
    try:
        # 1️⃣ KI Settings laden
        settings = db.query(AISettings).first()
        if not settings or not settings.active or not settings.api_key:
            return JSONResponse(
                {"error": "⚠️ KI ist nicht konfiguriert oder deaktiviert."},
                status_code=400
            )

        # 2️⃣ OpenAI Client initialisieren
        client = OpenAI(api_key=settings.api_key)

        # 3️⃣ User-Nachricht speichern
        user_msg = AIChatMessage(
            user_id=user.id,
            role="user",
            content=message
        )
        db.add(user_msg)
        db.commit()

        # 4️⃣ KI Antwort
        completion = client.chat.completions.create(
            model=settings.model or "gpt-4o-mini",
            messages=[
                {"role": "system",
                 "content": f"Du bist ein hilfreicher Assistent namens {settings.assistant_name}."},
                {"role": "user", "content": message}
            ],
            max_tokens=400
        )

        reply = completion.choices[0].message.content

        # 5️⃣ Antwort speichern
        bot_msg = AIChatMessage(
            user_id=user.id,
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


# =========================================================
# 🟦 KI Chat UI — GET
# =========================================================
@router.get("/assistant", response_class=HTMLResponse)
def assistant_ui(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Zeigt AI Chat-Oberfläche.
    """
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    settings = db.query(AISettings).first()
    error = None
    if not settings or not settings.api_key or not settings.active:
        error = "⚠️ KI ist nicht konfiguriert. Bitte API-Key speichern."

    is_admin = bool(user.role and user.role.name == "admin")

    return templates.TemplateResponse(
        "dashboard/ai_assistant.html",
        {
            "request": request,
            "is_admin": is_admin,
            "error": error
        }
    )