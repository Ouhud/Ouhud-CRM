# app/ai_assistant.py
import os
import time
from typing import List, Dict, Any

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

# ✅ geschützt: nur eingeloggte User
from app.auth import get_current_user, User

# Falls du das neue OpenAI SDK nutzt:
# from openai import OpenAI
# client = OpenAI()

# Falls du das "klassische" openai-Paket nutzt (wie bisher)
import openai

# -----------------------------------------------------------
# Router & Templates
# -----------------------------------------------------------
router = APIRouter(prefix="/dashboard/ai", tags=["AI Assistant"])
templates = Jinja2Templates(directory="templates")

# -----------------------------------------------------------
# Konfiguration
# -----------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()  # passe an, z.B. "gpt-4o" / "gpt-4" / "gpt-3.5-turbo"
SYSTEM_PROMPT  = (
    "Du bist ein hilfsbereiter, präziser CRM-Assistent für Ouhud CRM. "
    "Antworte kurz, klar und praxisnah. Wenn du unsicher bist, frage nach."
)

if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

# simples Rate-Limit pro Session (z.B. max 10 Anfragen pro 60 Sek.)
RATE_LIMIT_MAX_REQUESTS = 10
RATE_LIMIT_WINDOW_SEC   = 60

# -----------------------------------------------------------
# Hilfen: Chatverlauf & Rate-Limit in Session
# -----------------------------------------------------------
def _get_session_list(request: Request, key: str) -> List[Any]:
    if key not in request.session or not isinstance(request.session[key], list):
        request.session[key] = []
    return request.session[key]

def _push_chat_history(request: Request, role: str, content: str) -> None:
    history = _get_session_list(request, "ai_chat_history")
    history.append({"role": role, "content": content})
    # Verlauf auf z.B. letzte 16 User/Assistant-Nachrichten beschränken
    if len(history) > 16:
        request.session["ai_chat_history"] = history[-16:]

def _get_openai_messages_with_system(request: Request) -> List[Dict[str, str]]:
    history = _get_session_list(request, "ai_chat_history")
    return [{"role": "system", "content": SYSTEM_PROMPT}] + history

def _rate_limit_ok(request: Request) -> bool:
    now = time.time()
    bucket = _get_session_list(request, "ai_rate_times")
    # alte Einträge entfernen
    request.session["ai_rate_times"] = [t for t in bucket if now - t < RATE_LIMIT_WINDOW_SEC]
    bucket = request.session["ai_rate_times"]
    if len(bucket) >= RATE_LIMIT_MAX_REQUESTS:
        return False
    bucket.append(now)
    return True

# -----------------------------------------------------------
# UI: Seite anzeigen (geschützt)
# -----------------------------------------------------------
@router.get("/assistant", response_class=HTMLResponse)
def assistant_ui(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    if not OPENAI_API_KEY:
        # Zeig Hinweis in der UI, wenn Key fehlt
        return templates.TemplateResponse(
            "dashboard/ai_assistant.html",
            {
                "request": request,
                "error": "OPENAI_API_KEY fehlt in der Umgebung. Bitte setzen und Server neu starten."
            }
        )
    return templates.TemplateResponse(request, "dashboard/ai_assistant.html", {"request": request})

# -----------------------------------------------------------
# API: Frage stellen (Form oder JSON)
# -----------------------------------------------------------
@router.post("/query")
async def ai_query(
    request: Request,
    message: str = Form(None),
    current_user: User = Depends(get_current_user)
):
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY ist nicht gesetzt.")

    if not _rate_limit_ok(request):
        return JSONResponse(
            status_code=429,
            content={"error": "Zu viele Anfragen. Bitte kurz warten und erneut versuchen."}
        )

    # Falls JSON geschickt wurde, dort lesen
    if message is None:
        data = await request.json()
        message = (data or {}).get("message")

    if not message or not message.strip():
        return JSONResponse(status_code=400, content={"error": "Nachricht darf nicht leer sein."})

    # Verlauf aktualisieren (User)
    _push_chat_history(request, "user", message.strip())

    try:
        # ------- Variante klassisches SDK (kompatibel zu deinem Setup) -------
        completion = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=_get_openai_messages_with_system(request),
            temperature=0.2,
            max_tokens=500,
        )
        reply = completion.choices[0].message["content"]

        # ------- Variante neues SDK (falls du umstellst) -------
        # resp = client.chat.completions.create(
        #     model=OPENAI_MODEL,
        #     messages=_get_openai_messages_with_system(request),
        #     temperature=0.2,
        #     max_tokens=500,
        # )
        # reply = resp.choices[0].message.content

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"KI-Fehler: {e}"})

    # Verlauf aktualisieren (Assistant)
    _push_chat_history(request, "assistant", reply)

    return JSONResponse({"reply": reply})