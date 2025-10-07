# app/public_payment.py
import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Invoice, Customer

# 📌 Template-Verzeichnis festlegen
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "../templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# 📌 Router initialisieren
router = APIRouter(
    prefix="/pay",
    tags=["Zahlungen (Public)"]
)

# 🧾 Zahlungsseite (öffentlich zugänglich über Rechnungsnummer)
@router.get("/{invoice_number}", response_class=HTMLResponse)
def payment_page(request: Request, invoice_number: str, db: Session = Depends(get_db)):
    """
    Öffentliche Zahlungsseite anzeigen.
    Rechnung wird per Rechnungsnummer gesucht und die QR-Codes angezeigt.
    """

    # 1️⃣ Rechnung aus Datenbank holen
    invoice = db.query(Invoice).filter(Invoice.invoice_number == invoice_number).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")

    # 2️⃣ Kundendaten laden
    customer = db.query(Customer).filter(Customer.id == invoice.customer_id).first()

    # 3️⃣ Template rendern
    return templates.TemplateResponse(
        "payment/pay_invoice.html",
        {
            "request": request,
            "invoice": invoice,
            "customer": customer,
            "datetime": datetime,  # ✅ für Footer-Jahr
        }
    )