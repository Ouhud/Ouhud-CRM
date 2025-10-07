# app/invoices.py
from __future__ import annotations

import os
from datetime import date
from typing import List


from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

# 📌 Projekt-Module
from app.database import get_db
from app.models import Invoice, InvoiceItem, InvoiceStatus, User   # ✅ User statt UserDB
from app.auth import get_current_user
from app.permissions import require_role
from app.utils.pdf_utils import generate_invoice_pdf
from app.utils import qrcode_utils   # ✅ QR-Code Modul

router = APIRouter(
    prefix="/invoices",
    tags=["Rechnungen"]
)


# 📝 Pydantic Schemas
class InvoiceItemCreate(BaseModel):
    description: str
    quantity: int
    unit_price: float


class InvoiceCreate(BaseModel):
    customer_id: int
    invoice_number: str
    date: date
    due_date: date
    items: List[InvoiceItemCreate]


class InvoiceOut(BaseModel):
    id: int
    invoice_number: str
    date: date
    due_date: date
    status: str
    total_amount: float

    model_config = ConfigDict(from_attributes=True)


# 🧾 📌 Rechnung erstellen + QR-Codes generieren
@router.post("/", response_model=InvoiceOut)
def create_invoice(
    invoice_data: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)   # ✅
):
    # ✅ Nur Admin oder Mitarbeiter dürfen Rechnungen erstellen
    require_role(current_user, ["admin", "mitarbeiter"])

    # 1️⃣ Neue Rechnung anlegen
    new_invoice = Invoice(
        customer_id=invoice_data.customer_id,
        invoice_number=invoice_data.invoice_number,
        date=invoice_data.date,
        due_date=invoice_data.due_date,
        status=InvoiceStatus.draft
    )

    # 2️⃣ Positionen & Gesamtbetrag berechnen
    total = 0
    for item in invoice_data.items:
        total += item.quantity * item.unit_price
        db_item = InvoiceItem(
            description=item.description,
            quantity=item.quantity,
            unit_price=item.unit_price
        )
        new_invoice.items.append(db_item)

    new_invoice.total_amount = total
    db.add(new_invoice)
    db.commit()
    db.refresh(new_invoice)

    # 3️⃣ QR-Codes generieren
    invoice_number = new_invoice.invoice_number
    amount = float(new_invoice.total_amount)

    # 🌐 Online-Link (Public Payment Page)
    payment_url = f"https://ouhud.com/pay/{invoice_number}"
    qrcode_utils.generate_link_qr(payment_url, f"link_{invoice_number}")

    # 🇪🇺 SEPA-QR
    iban = "DE02120300000000202051"  # ⚠️ Richtige IBAN hier eintragen
    company_name = "Hamza Dev GmbH"
    purpose = f"Rechnung {invoice_number}"
    qrcode_utils.generate_sepa_qr(
        iban=iban,
        name=company_name,
        amount=amount,
        purpose=purpose,
        filename=f"sepa_{invoice_number}"
    )

    # 🇨🇭 TWINT / Swiss QR (vereinfachte Version)
    qrcode_utils.generate_twint_qr(
        iban=iban,
        reference=invoice_number,
        amount=amount,
        currency="CHF",
        filename=f"twint_{invoice_number}",
        company_name=company_name,
        company_address="Musterstrasse 1",
        company_zip_city="8000 Zürich"
    )

    return new_invoice


# 📋 Alle Rechnungen abrufen
@router.get("/", response_model=List[InvoiceOut])
def get_invoices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    require_role(current_user, ["admin", "mitarbeiter"])  # ✅ angepasst
    return db.query(Invoice).all()


# 📄 Rechnung als PDF herunterladen
@router.get("/{invoice_id}/pdf")
def download_invoice_pdf(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    require_role(current_user, ["admin", "mitarbeiter"])  # ✅ angepasst

    # 1️⃣ Rechnung laden
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")

    customer = invoice.customer
    if not customer:
        raise HTTPException(status_code=400, detail="Kundendaten fehlen für PDF-Erzeugung")

    # 2️⃣ PDF erzeugen
    try:
        file_path = generate_invoice_pdf(invoice, invoice.items, customer)
    except Exception as e:
        import traceback, logging
        logging.error("Fehler bei PDF-Erzeugung: %s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Fehler bei PDF-Erzeugung: {str(e)}")

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=500, detail="PDF konnte nicht erzeugt werden")

    # 3️⃣ PDF senden
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=f"Rechnung_{invoice.invoice_number}.pdf",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Content-Disposition": f'inline; filename="Rechnung_{invoice.invoice_number}.pdf"'
        }
    )