# app/utils/ai_provider.py
from __future__ import annotations
import os
import json
import time
import logging
from typing import Optional, Any, Dict, List

import requests
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import AISettings


# ---------------------------------------------------------------------
# LOGGING (für alle KI Provider einheitlich)
# ---------------------------------------------------------------------
logger = logging.getLogger("AIProvider")
logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------
def safe_value(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if hasattr(value, "expression"):
        return default
    if isinstance(value, (str, int, float, bool)):
        return value
    return default


# ---------------------------------------------------------------------
# Provider → erlaubte Modelle
# ---------------------------------------------------------------------
PROVIDER_MODELS: Dict[str, List[str]] = {
    "openai": [
        "gpt-5.1",
        "gpt-4.1",
        "gpt-4o",
        "gpt-4o-mini",
    ],
    "gemini": [
        "gemini-2.0-flash",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
    ],
    "groq": [
        "mixtral-8x7b",
        "gemma2-9b-it",
        "llama3-70b",
        "llama3-8b",
    ],
    "anthropic": [
        "claude-3-opus",
        "claude-3-sonnet",
        "claude-3-haiku",
    ],
    "openrouter": [
        "openai/gpt-4.1",
        "google/gemini-pro",
        "meta/llama3-70b",
    ],
}


# ---------------------------------------------------------------------
# UNIVERSAL AI PROVIDER – ENTERPRISE
# ---------------------------------------------------------------------
class AIProvider:

    def __init__(self, user_choice_model: Optional[str] = None):

        db: Session = SessionLocal()
        settings: Optional[AISettings] = db.query(AISettings).first()
        db.close()

        # Provider
        self.provider: str = safe_value(
            settings.provider if settings else None,
            os.getenv("AI_PROVIDER", "openai")
        ).lower()

        # Modell mit Autovervollständigung
        db_model = safe_value(
            settings.model if settings else None,
            os.getenv("AI_MODEL", "gpt-5.1")
        )

        self.model = user_choice_model or db_model
        self.model = self._validate_model(self.provider, self.model)

        # API Key
        self.api_key = safe_value(settings.api_key if settings else None,
                                  os.getenv("OPENAI_API_KEY", ""))

        # Aktiv
        self.active: bool = bool(
            safe_value(settings.active if settings else False, False)
        )

        # Zeitüberschreitung & Retry Einstellungen
        self.timeout = 30
        self.max_retries = 3

        # Fallback Provider
        self.fallback_provider = "openrouter"

    # -----------------------------------------------------------------
    # Modell Validierung + Auto-Korrektur
    # -----------------------------------------------------------------
    def _validate_model(self, provider: str, model: str) -> str:

        allowed = PROVIDER_MODELS.get(provider, [])

        if model in allowed:
            return model

        # Wenn Modell unbekannt → erstes erlaubtes Modell nehmen
        if allowed:
            logger.warning(f"[AI] Modell '{model}' ungültig für Provider '{provider}'.")
            logger.warning(f"[AI] Setze automatisch Modell: {allowed[0]}")
            return allowed[0]

        return model

    # -----------------------------------------------------------------
    # Hauptmethode
    # -----------------------------------------------------------------
    def chat(self, prompt: str) -> str:

        if not self.active:
            return "⚠️ KI deaktiviert."

        if not self.api_key:
            return "⚠️ Kein API Key gespeichert."

        # Retry Mechanismus
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"[AI] Provider={self.provider}, Modell={self.model}, Versuch {attempt}")

                match self.provider:
                    case "openai":
                        return self._openai(prompt)
                    case "gemini":
                        return self._gemini(prompt)
                    case "anthropic":
                        return self._anthropic(prompt)
                    case "groq":
                        return self._groq(prompt)
                    case "openrouter":
                        return self._openrouter(prompt)

                return "⚠️ Unbekannter Provider."

            except Exception as e:
                logger.error(f"[AI] Fehler Versuch {attempt}: {e}")
                time.sleep(2)

        # Fallback Provider
        logger.warning("[AI] Wechsel zum Fallback Provider → OpenRouter")
        self.provider = self.fallback_provider
        self.model = PROVIDER_MODELS[self.fallback_provider][0]
        return self._openrouter(prompt)

    # -----------------------------------------------------------------
    # OPENAI API
    # -----------------------------------------------------------------
    def _openai(self, prompt: str) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)

        res = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Antworte nur in JSON."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=500,
            timeout=self.timeout
        )

        return res.choices[0].message.content

    # -----------------------------------------------------------------
    # GOOGLE GEMINI API
    # -----------------------------------------------------------------
    def _gemini(self, prompt: str) -> str:
        import google.generativeai as genai

        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(self.model)
        response = model.generate_content(prompt)
        return response.text

    # -----------------------------------------------------------------
    # CLAUDE / ANTHROPIC
    # -----------------------------------------------------------------
    def _anthropic(self, prompt: str) -> str:
        import anthropic

        client = anthropic.Anthropic(api_key=self.api_key)
        result = client.messages.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
        )
        return result.content[0].text

    # -----------------------------------------------------------------
    # GROQ
    # -----------------------------------------------------------------
    def _groq(self, prompt: str) -> str:
        from groq import Groq

        client = Groq(api_key=self.api_key)
        res = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        return res.choices[0].message.content

    # -----------------------------------------------------------------
    # OPENROUTER (Fallback Provider)
    # -----------------------------------------------------------------
    def _openrouter(self, prompt: str) -> str:
        url = "https://openrouter.ai/api/v1/chat/completions"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Antworte nur in JSON."},
                {"role": "user", "content": prompt},
            ]
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        r = requests.post(url, json=payload, headers=headers, timeout=self.timeout)

        data = r.json()
        if "choices" not in data:
            raise ValueError(f"Ungültige OpenRouter Antwort: {data}")

        return data["choices"][0]["message"]["content"]