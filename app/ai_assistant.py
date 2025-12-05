# app/ai_assistant.py
import os
import time
from typing import List, Dict, Optional

from fastapi import (
    APIRouter, Request, Depends, Form, HTTPException
)
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import Session

# Auth / Tenant
from app.auth import get_current_user, User
from app.database import get_db
from app.models import AISettings, AIMessageLog

# Provider SDKs
import openai
import google.generativeai as genai
import requests

# ----------------------------------------------------------
# GLOBAL SETTINGS
# ----------------------------------------------------------
router = APIRouter(prefix="/dashboard/ai", tags=["AI Assistant"])
templates = Jinja2Templates(directory="templates")

SUPPORTED_PROVIDERS = ["openai", "groq", "gemini", "openrouter"]

DEFAULT_SYSTEM_PROMPT = (
    "Du bist ein professioneller KI-Assistent für Ouhud CRM. "
    "Du beantwortest Fragen kurz, präzise und geschäftsorientiert."
)

RATE_LIMIT_MAX = 10
RATE_LIMIT_WINDOW = 60     # Sekunden

# ----------------------------------------------------------
# Provider Clients dynamisch erzeugen
# ----------------------------------------------------------
def load_provider_client(provider: str, key: str):
    if provider == "openai":
        openai.api_key = key
        return None  # openai nutzt globales Objekt

    if provider == "gemini":
        genai.configure(api_key=key)
        return genai.GenerativeModel("gemini-1.5-flash")

    if provider == "groq":
        return key  # wir nutzen requests direkt

    if provider == "openrouter":
        return key  # ebenfalls requests

    raise ValueError("Unbekannter Provider")


# ----------------------------------------------------------
# Datenbank-Layer: AI Settings laden
# ----------------------------------------------------------
def load_ai_settings(db: Session, user: User) -> AISettings:
    settings = (
        db.query(AISettings)
        .filter(AISettings.company_id == user.company_id)
        .first()
    )
    if not settings:
        raise HTTPException(400, "AI-Einstellungen fehlen. Bitte konfigurieren.")
    if not settings.api_key:
        raise HTTPException(400, "API-Key fehlt. Bitte Einstellungen aktualisieren.")
    return settings


# ----------------------------------------------------------
# CHAT-HISTORY & RATE LIMIT
# ----------------------------------------------------------
def get_list(request: Request, key: str):
    if key not in request.session:
        request.session[key] = []
    return request.session[key]


def push_history(request: Request, role: str, content: str):
    hist = get_list(request, "ai_history")
    hist.append({"role": role, "content": content})
    request.session["ai_history"] = hist[-20:]  # letzter Chatverlauf


def rate_limit_ok(request: Request):
    now = time.time()
    bucket = get_list(request, "ai_times")
    request.session["ai_times"] = [t for t in bucket if now - t < RATE_LIMIT_WINDOW]
    bucket = request.session["ai_times"]
    if len(bucket) >= RATE_LIMIT_MAX:
        return False
    bucket.append(now)
    return True


# ----------------------------------------------------------
# RENDER CHAT UI + HISTORY
# ----------------------------------------------------------
@router.get("/assistant", response_class=HTMLResponse)
def ui_assistant(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    # ⬅️ Verlauf laden (komplette Historie aus DB)
    history = db.query(AIMessageLog)\
        .filter_by(user_id=user.id)\
        .order_by(AIMessageLog.id.asc())\
        .all()

    return templates.TemplateResponse(
        "dashboard/ai_assistant.html",
        {
            "request": request,
            "user": user,
            "history": history,   # ⬅️ an Frontend geben
        }
    )

# ----------------------------------------------------------
# KI ANFRAGE ABSENDEN
# ----------------------------------------------------------
@router.post("/query")
async def ai_query(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    message: Optional[str] = Form(None)
):
    # Rate-Limit prüfen
    if not rate_limit_ok(request):
        return JSONResponse({"error": "Rate-Limit erreicht. Bitte warten."}, 429)

    # Nachricht aus JSON extrahieren, falls nicht per Form gesendet
    if message is None:
        body = await request.json()
        message = body.get("message")

    if not message or message.strip() == "":
        return JSONResponse({"error": "Nachricht darf nicht leer sein."}, 400)

    # AI Settings laden
    settings = load_ai_settings(db, user)
    provider = settings.provider
    api_key = settings.api_key
    model = settings.model

    # ----------------------------------------------------------
    # 1️⃣ USER Nachricht in DB speichern
    # ----------------------------------------------------------
    db.add(AIChatHistory(
        user_id=user.id,
        company_id=user.company_id,
        role="user",
        message=message
    ))
    db.commit()

    # Verlauf (Session) aktualisieren
    push_history(request, "user", message)

    # Systemprompt + Verlauf kombinieren
    history = [{"role": "system", "content": DEFAULT_SYSTEM_PROMPT}]
    history += get_list(request, "ai_history")

    # ----------------------------------------------------------
    # 2️⃣ KI Antwort erzeugen
    # ----------------------------------------------------------
    try:
        reply, tokens, cost = await call_ai_provider(
            provider, api_key, model, history
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, 500)

    # Verlauf (Session) aktualisieren
    push_history(request, "assistant", reply)

    # ----------------------------------------------------------
    # 3️⃣ ASSISTANT Antwort in DB speichern
    # ----------------------------------------------------------
    db.add(AIChatHistory(
        user_id=user.id,
        company_id=user.company_id,
        role="assistant",
        message=reply
    ))
    db.commit()

    # ----------------------------------------------------------
    # 4️⃣ Logging (Analytics)
    # ----------------------------------------------------------
    log = AIMessageLog(
        user_id=user.id,
        company_id=user.company_id,
        provider=provider,
        model=model,
        question=message,
        answer=reply,
        tokens_used=tokens,
        cost_usd=cost
    )
    db.add(log)
    db.commit()

    # ----------------------------------------------------------
    # 5️⃣ JSON Response zurückgeben
    # ----------------------------------------------------------
    return JSONResponse({
        "reply": reply,
        "tokens": tokens,
        "cost": cost
    })

# ----------------------------------------------------------
# Provider Dispatcher
# ----------------------------------------------------------
async def call_ai_provider(
    provider: str,
    key: str,
    model: str,
    messages: List[Dict]
):
    provider = provider.lower()

    if provider == "openai":
        return call_openai(key, model, messages)

    if provider == "gemini":
        return call_gemini(key, model, messages)

    if provider == "groq":
        return call_groq(key, model, messages)

    if provider == "openrouter":
        return call_openrouter(key, model, messages)

    raise Exception("Unbekannter Provider")


# ----------------------------------------------------------
# Provider: OpenAI
# ----------------------------------------------------------
def call_openai(api_key, model, messages):
    openai.api_key = api_key
    resp = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=0.3,
    )
    reply = resp.choices[0].message["content"]
    tokens = resp.usage.total_tokens
    cost = tokens * 0.000002  # Beispielpreis
    return reply, tokens, cost


# ----------------------------------------------------------
# Provider: Gemini
# ----------------------------------------------------------
def call_gemini(api_key, model, messages):
    genai.configure(api_key=api_key)
    gem = genai.GenerativeModel(model)
    prompt = "\n".join(m["content"] for m in messages)
    resp = gem.generate_content(prompt)
    reply = resp.text
    tokens = resp.usage_metadata.total_token_count
    cost = tokens * 0.0000005
    return reply, tokens, cost


# ----------------------------------------------------------
# Provider: Groq (HTTP API)
# ----------------------------------------------------------
def call_groq(api_key, model, messages):
    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": model,
        "messages": messages
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    r = requests.post(url, json=payload, headers=headers)
    data = r.json()
    reply = data["choices"][0]["message"]["content"]
    tokens = data["usage"]["total_tokens"]
    cost = tokens * 0.000001
    return reply, tokens, cost


# ----------------------------------------------------------
# Provider: OpenRouter
# ----------------------------------------------------------
def call_openrouter(api_key, model, messages):
    url = "https://openrouter.ai/api/v1/chat/completions"
    payload = {"model": model, "messages": messages}
    headers = {"Authorization": f"Bearer {api_key}"}
    r = requests.post(url, json=payload, headers=headers)
    data = r.json()
    reply = data["choices"][0]["message"]["content"]
    tokens = data["usage"]["total_tokens"]
    cost = tokens * 0.0000025
    return reply, tokens, cost


from fastapi.responses import StreamingResponse

@router.post("/stream")
async def ai_stream(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    body = await request.json()
    message = body.get("message")

    settings = load_ai_settings(db, user)

    history = [{"role": "system", "content": DEFAULT_SYSTEM_PROMPT}]
    history += get_list(request, "ai_history")

    # OPENAI Beispiel – andere Provider möglich
    openai.api_key = settings.api_key

    def event_generator():
        with openai.ChatCompletion.create(
            model=settings.model,
            messages=history + [{"role": "user", "content": message}],
            stream=True
        ) as stream:
            for chunk in stream:
                if "content" in chunk["choices"][0]["delta"]:
                    text = chunk["choices"][0]["delta"]["content"]
                    yield f"data: {text}\n\n"

        yield "data: [STREAM_END]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

