# app/inbox.py
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime
from fastapi.templating import Jinja2Templates
import os

from app.database import get_db
from app.auth import require_login
from app.models import Message, Customer

router = APIRouter(prefix="/dashboard/inbox", tags=["Inbox"])

# 📁 Templates-Verzeichnis global festlegen
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


# 📬 Inbox Hauptseite (mit Filter und Suche)
@router.get("/", response_class=HTMLResponse)
def inbox_list(
    request: Request,
    db: Session = Depends(get_db),
    q: str | None = None,
    show: str | None = "open"   # open | archived | all
):
    user = request.state.user
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    query = db.query(Message)

    # 🔍 Filter
    if show == "open":
        query = query.filter(Message.is_archived == False)
    elif show == "archived":
        query = query.filter(Message.is_archived == True)

    # 🔍 Suche (Betreff, Text, Absender)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Message.subject.ilike(like),
                Message.sender_name.ilike(like),
                Message.sender_email.ilike(like),
                Message.content.ilike(like),
            )
        )

    messages = query.order_by(Message.received_at.desc()).all()

    # 🧮 Kennzahlen
    open_count = db.query(Message).filter(Message.is_archived == False).count()
    archived_count = db.query(Message).filter(Message.is_archived == True).count()

    return templates.TemplateResponse(
        "inbox.html",
        {
            "request": request,
            "messages": messages,
            "user": user,
            "q": q or "",
            "show": show,
            "open_count": open_count,
            "archived_count": archived_count,
        },
    )


# ✅ Nachricht als gelesen/ungelesen markieren
@router.post("/{message_id}/toggle-read")
def toggle_read(message_id: int, request: Request, db: Session = Depends(get_db)):
    user = request.state.user
    if not user:
        return RedirectResponse("/auth/login", status_code=303)

    msg = db.query(Message).get(message_id)
    if not msg:
        raise HTTPException(404, "Nachricht nicht gefunden")

    msg.is_read = not msg.is_read
    db.commit()
    return RedirectResponse(url="/dashboard/inbox", status_code=303)


# 📂 Nachricht archivieren oder wiederherstellen
@router.post("/{message_id}/toggle-archive")
def toggle_archive(message_id: int, request: Request, db: Session = Depends(get_db)):
    user = request.state.user
    if not user:
        return RedirectResponse("/auth/login", status_code=303)

    msg = db.query(Message).get(message_id)
    if not msg:
        raise HTTPException(404, "Nachricht nicht gefunden")

    msg.is_archived = not msg.is_archived
    db.commit()
    return RedirectResponse(url="/dashboard/inbox", status_code=303)


# 📝 Nachricht beantworten (SMTP kommt später)
@router.post("/{message_id}/reply")
def reply_message(
    message_id: int,
    request: Request,
    db: Session = Depends(get_db),
    body: str = Form(...)
):
    user = request.state.user
    if not user:
        return RedirectResponse("/auth/login", status_code=303)

    msg = db.query(Message).get(message_id)
    if not msg:
        raise HTTPException(404, "Nachricht nicht gefunden")

    # 📬 Simulation: Ausgabe in Konsole (SMTP kannst du hier einbauen)
    print(f"📨 Reply an {msg.sender_email} (Betreff: Re: {msg.subject})")
    print(f"---\n{body}\n---")

    msg.is_read = True
    db.commit()

    return RedirectResponse(url="/dashboard/inbox", status_code=303)


# 🗑 Nachricht löschen
@router.post("/{message_id}/delete")
def delete_message(message_id: int, request: Request, db: Session = Depends(get_db)):
    user = request.state.user
    if not user:
        return RedirectResponse("/auth/login", status_code=303)

    msg = db.query(Message).get(message_id)
    if not msg:
        raise HTTPException(404, "Nachricht nicht gefunden")

    db.delete(msg)
    db.commit()
    return RedirectResponse(url="/dashboard/inbox", status_code=303)

# ➕ Neue Nachricht erstellen (z.B. über internes Formular)
@router.post("/create")
def create_message(
    request: Request,
    db: Session = Depends(get_db),
    sender_name: str = Form(...),
    sender_email: str = Form(...),
    subject: str = Form(...),
    content: str = Form(...)
):
    # 🧑‍💻 Login prüfen
    user = request.state.user
    if not user:
        return RedirectResponse("/auth/login", status_code=303)

    # 📌 Kunde automatisch verknüpfen, falls E-Mail bekannt
    customer = db.query(Customer).filter(Customer.email == sender_email).first()

    # 📨 Neue Nachricht speichern
    new_message = Message(
        sender_name=sender_name.strip(),
        sender_email=sender_email.strip().lower(),
        subject=subject.strip(),
        content=content.strip(),
        received_at=datetime.utcnow(),
        customer=customer
    )
    db.add(new_message)
    db.commit()

    # 📬 Zur Inbox zurückleiten
    return RedirectResponse(url="/dashboard/inbox", status_code=303)