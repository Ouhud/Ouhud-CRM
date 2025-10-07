# app/reminders.py
import os
from datetime import date

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import require_login
from app.models import Invoice
from app.utils.pdf_utils import generate_invoice_pdf

# ─────────────────────────────
# 📌 Router Setup
# ─────────────────────────────
router = APIRouter(
    prefix="/dashboard/invoices/reminders",
    tags=["Reminders"]
)

# ─────────────────────────────
# 🧭 Templates
# ─────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


# ─────────────────────────────
# 📨 1️⃣ Aktive Mahnungen anzeigen
# ─────────────────────────────
@router.get("/", response_class=HTMLResponse)
def reminders_list(request: Request, db: Session = Depends(get_db)):
    user = require_login(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    reminders = (
        db.query(Invoice)
        .filter(Invoice.reminder_level > 0)
        .order_by(Invoice.due_date.asc())
        .all()
    )

    return templates.TemplateResponse(
        "reminders.html",
        {"request": request, "reminders": reminders, "user": user}
    )


# ─────────────────────────────
# 📄 2️⃣ Mahnung als PDF herunterladen
# ─────────────────────────────
@router.get("/pdf/{invoice_id}")
def download_reminder_pdf(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")

    customer = invoice.customer
    file_path = generate_invoice_pdf(invoice, invoice.items, customer)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=500, detail="PDF konnte nicht erzeugt werden")

    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=f"Mahnung_{invoice.invoice_number}.pdf"
    )


# ─────────────────────────────
# ✉️ 3️⃣ Mahnung per E-Mail senden (Platzhalter)
# ─────────────────────────────
@router.get("/send/{invoice_id}")
def send_reminder(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")

    # TODO: Hier echte E-Mail-Funktion implementieren
    print(f"✉️ Mahnung für Rechnung {invoice.invoice_number} wurde (simuliert) gesendet.")

    return RedirectResponse(
        url="/dashboard/invoices/reminders",
        status_code=303
    )


# ─────────────────────────────
# 🗑 4️⃣ Mahnung löschen (Reminder-Level zurücksetzen)
# ─────────────────────────────
@router.get("/delete/{invoice_id}")
def delete_reminder(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")

    invoice.reminder_level = 0
    db.commit()

    return RedirectResponse(
        url="/dashboard/invoices/reminders",
        status_code=303
    )