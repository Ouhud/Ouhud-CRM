# app/chat.py
import os
from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from app.models import ChatMessage
from app.database import SessionLocal

router = APIRouter(prefix="/dashboard/chat", tags=["Team Chat"])

# 📌 Templates
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# 🌐 Aktive WebSocket-Verbindungen
active_connections: List[WebSocket] = []


# ─────────────────────────────────────────────
# 💬 Chat UI (HTML)
# ─────────────────────────────────────────────
@router.get("/", response_class=HTMLResponse)
async def chat_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "team_chat.html",
        {"request": request}
    )


# ─────────────────────────────────────────────
# 📜 Chat-Historie (mit Typen → keine Warnungen)
# ─────────────────────────────────────────────
@router.get("/history")
async def chat_history() -> List[Dict[str, Any]]:
    db = SessionLocal()
    messages = db.query(ChatMessage).order_by(ChatMessage.timestamp.asc()).all()
    db.close()

    result: List[Dict[str, Any]] = []

    for msg in messages:
        result.append({
            "sender": msg.sender,
            "text": msg.message,
            "timestamp": msg.timestamp.strftime("%H:%M:%S")
        })

    return result


# ─────────────────────────────────────────────
# 📡 WebSocket Endpoint
# ─────────────────────────────────────────────
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    active_connections.append(websocket)
    await broadcast_online_count()

    try:
        while True:
            data: Dict[str, Any] = await websocket.receive_json()

            # Ping/Pong
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            # Neue Nachricht
            if data.get("type") == "message":
                sender: str = "Ich"
                text: str = data["text"]

                # Speichern
                db = SessionLocal()
                new_msg = ChatMessage(sender=sender, message=text)
                db.add(new_msg)
                db.commit()
                db.close()

                await broadcast_message(sender, text)

    except WebSocketDisconnect:
        active_connections.remove(websocket)
        await broadcast_online_count()


# ─────────────────────────────────────────────
# 📢 Broadcast Nachricht (mit Typen)
# ─────────────────────────────────────────────
async def broadcast_message(sender: str, text: str) -> None:
    payload: Dict[str, Any] = {
        "type": "message",
        "sender": sender,
        "text": text
    }

    for conn in active_connections:
        await conn.send_json(payload)


# ─────────────────────────────────────────────
# 📢 Broadcast Online-Zähler
# ─────────────────────────────────────────────
async def broadcast_online_count() -> None:
    payload: Dict[str, int] = {
        "type": "presence",
        "online": len(active_connections),
    }

    for conn in active_connections:
        await conn.send_json(payload)