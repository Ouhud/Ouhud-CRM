import os
from datetime import datetime
from typing import List
import requests

from fastapi import (
    APIRouter, Request, Form, Depends, WebSocket, WebSocketDisconnect
)
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import WhatsAppMessage, WhatsAppSettings

router = APIRouter(prefix="/dashboard/whatsapp", tags=["WhatsApp"])

# 📌 Template-Verzeichnis
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


# 🧰 DB-Session-Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 🧭 Aktive WebSocket-Verbindungen speichern
active_connections: List[WebSocket] = []


# 🌐 Verbindung prüfen (für UI)
@router.get("/status")
async def whatsapp_status(db: Session = Depends(get_db)):
    settings = db.query(WhatsAppSettings).first()
    return JSONResponse({"connected": settings is not None})


# 🧭 Chat-Oberfläche
@router.get("/", response_class=HTMLResponse)
async def whatsapp_page(request: Request):
    return templates.TemplateResponse(request, "whatsapp_chat.html", {"request": request})


# 📝 Zugangsdaten-Formular
@router.get("/connect", response_class=HTMLResponse)
async def whatsapp_connect_page(request: Request):
    return templates.TemplateResponse(request, "whatsapp_connect.html", {"request": request})


# 💾 Zugangsdaten speichern
@router.post("/save_credentials")
async def save_whatsapp_credentials(
    phone_number_id: str = Form(...),
    business_id: str = Form(...),
    access_token: str = Form(...),
    db: Session = Depends(get_db)
):
    existing = db.query(WhatsAppSettings).first()
    if existing:
        db.delete(existing)
        db.commit()

    settings = WhatsAppSettings(
        company_id=1,
        phone_number="+unknown",
        phone_number_id=phone_number_id,
        business_id=business_id,
        access_token=access_token
    )
    db.add(settings)
    db.commit()

    return RedirectResponse(url="/dashboard/whatsapp", status_code=303)


# 📥 Nachrichten laden (initial)
@router.get("/messages")
async def whatsapp_messages(db: Session = Depends(get_db)):
    messages = db.query(WhatsAppMessage).order_by(WhatsAppMessage.timestamp.asc()).all()
    data = [
        {"from": m.from_number, "text": m.message, "time": m.timestamp.isoformat()}
        for m in messages
    ]
    return JSONResponse(content=data)


# 🌐 WebSocket — Live-Kommunikation
@router.websocket("/ws")
async def whatsapp_ws(websocket: WebSocket):
    """Echtzeitverbindung für neue Nachrichten."""
    await websocket.accept()
    active_connections.append(websocket)
    print(f"✅ Neue WS-Verbindung ({len(active_connections)} aktiv)")

    try:
        while True:
            # optional: falls der Client auch Nachrichten schicken möchte
            data = await websocket.receive_text()
            print(f"📥 WebSocket empfangen: {data}")
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        print("❌ WebSocket Client getrennt")


# 📤 Nachricht senden (Meta API + Push an WebSocket)
@router.post("/send")
async def send_whatsapp_message(
    to: str = Form(...),
    text: str = Form(...),
    db: Session = Depends(get_db)
):
    """Nachricht senden → Meta API → DB speichern → Live an WebSocket-Clients pushen."""
    settings = db.query(WhatsAppSettings).first()
    if not settings:
        return JSONResponse({"error": "WhatsApp nicht verbunden"}, status_code=400)

    # 📨 Meta Cloud API Request
    url = f"https://graph.facebook.com/v17.0/{settings.phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        return JSONResponse(
            {"error": "Fehler beim Senden über Meta API", "details": response.json()},
            status_code=response.status_code
        )

    # 📝 Nachricht lokal speichern
    msg = WhatsAppMessage(
        from_number="Business",
        to_number=to,
        message=text,
        timestamp=datetime.utcnow()
    )
    db.add(msg)
    db.commit()

    # 📡 Echtzeit-Push an alle verbundenen Clients
    for connection in active_connections:
        await connection.send_json({
            "from": msg.from_number,
            "to": msg.to_number,
            "text": msg.message,
            "time": msg.timestamp.isoformat()
        })

    return JSONResponse({"status": "sent", "to": to, "text": text})