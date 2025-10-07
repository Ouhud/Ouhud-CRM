# app/chat.py
import os
from datetime import datetime
from typing import List
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

# ────────────────────────────────
# 💬 Chat-Oberfläche
# ────────────────────────────────
@router.get("/", response_class=HTMLResponse)
async def chat_page(request: Request):
    return templates.TemplateResponse(request, "team_chat.html", {"request": request})

# ────────────────────────────────
# 📡 WebSocket (Echtzeit Chat)
# ────────────────────────────────
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()

            # 📝 Nachricht speichern in DB
            db = SessionLocal()
            new_msg = ChatMessage(sender="Team", message=data)
            db.add(new_msg)
            db.commit()
            db.close()

            # 🕓 Zeitstempel für UI
            timestamp = datetime.utcnow().strftime("%H:%M:%S")
            formatted = f"[{timestamp}] Team: {data}"

            # 📢 Broadcast an alle verbundenen Clients
            for conn in active_connections:
                await conn.send_text(formatted)
    except WebSocketDisconnect:
        active_connections.remove(websocket)