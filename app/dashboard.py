# app/dashboard.py

import os
from datetime import date
from pathlib import Path

from fastapi import (
    APIRouter, Request, Depends, Form, UploadFile
)
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import require_login
from app.database import get_db
from app.models import Customer, Invoice, InvoiceItem, CompanySettings
from app.utils.pdf_utils import generate_invoice_pdf

from fastapi.background import BackgroundTasks
from app.utils.pdf_utils import generate_invoice_pdf
from app.utils.email_utils import send_invoice_email  # 📌 diese Funktion musst du gleich anlegen


# 📥 CAMT.053 Datei-Upload & Zahlungsabgleich
from fastapi import UploadFile, File
from app.utils.camt_parser import parse_camt053
from datetime import date


from app.models import InvoiceStatus   # ⚠️ wichtig, damit der Enum erkannt wird


# 📌 Router für Dashboard
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

# 📁 Templates-Verzeichnis
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)
# 🏠 Dashboard-Startseite
@router.get("/", response_class=HTMLResponse)
def dashboard_home(request: Request, db: Session = Depends(get_db)):
    # ✅ Login prüfen
    user = require_login(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    # 📊 Basiszahlen
    customer_count = db.query(Customer).count()
    invoice_count = db.query(Invoice).count()
    total_sum = sum(float(i.total_amount) for i in db.query(Invoice).all())

    # 📌 Offene Rechnungen analysieren
    open_invoices = db.query(Invoice).filter(
        Invoice.status.in_([InvoiceStatus.sent, InvoiceStatus.reminder])
    ).all()

    overdue_count = sum(1 for i in open_invoices if i.due_date < date.today())
    reminder_count = sum(1 for i in open_invoices if getattr(i, "reminder_level", 0) > 0)

    stats = {
        "customers": customer_count,
        "invoices": invoice_count,
        "total_sum": total_sum,
        "overdue": overdue_count,
        "reminders": reminder_count
    }

    # 🏢 Firmendaten (z. B. für Währung)
    company = db.query(CompanySettings).first()

    # 📝 Normales Benutzer-Dashboard zurückgeben
    return templates.TemplateResponse(
        "dashboard.html",    # ✅ eigenes Dashboard-Template für Benutzer
        {
            "request": request,
            "user": user,
            "stats": stats,
            "company": company
        }
    )

# 👥 Kundenübersicht
@router.get("/customers", response_class=HTMLResponse)
def customers_list(request: Request, db: Session = Depends(get_db)):
    user = require_login(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    customers = db.query(Customer).all()
    return templates.TemplateResponse(
        "admin/customers.html",
        {"request": request, "customers": customers, "user": user}
    )


# ➕ Kunde erstellen (Form)
@router.get("/customers/create", response_class=HTMLResponse)
def customer_create_form(request: Request, db: Session = Depends(get_db)):
    user = require_login(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    return templates.TemplateResponse(request, "admin/customers_form.html", {"request": request, "user": user})


from datetime import datetime
from fastapi import HTTPException

@router.post("/customers/create")
def customer_create(
    name: str = Form(...),
    email: str = Form(...),
    address: str = Form(None),
    city: str = Form(None),
    country: str = Form(...),    # Land als Pflichtfeld
    phone: str = Form(None),
    db: Session = Depends(get_db)
):
    # 1️⃣ Dublettenprüfung nach E-Mail
    existing = db.query(Customer).filter(Customer.email == email).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Ein Kunde mit der E-Mail {email} existiert bereits."
        )

    # 2️⃣ Kundennummer generieren
    year = datetime.now().year
    count = db.query(Customer).count() + 1
    customer_number = f"C-{year}-{count:05d}"

    # 3️⃣ Kundenobjekt erstellen
    new_customer = Customer(
        customer_number=customer_number,
        name=name,
        email=email,
        address=address,
        city=city,
        country=country,
        phone=phone
    )

    # 4️⃣ Speichern
    db.add(new_customer)
    db.commit()

    return RedirectResponse(url="/dashboard/customers", status_code=303)

# ✏️ Kunde bearbeiten
@router.get("/customers/edit/{customer_id}", response_class=HTMLResponse)
def customer_edit_form(customer_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_login(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    customer = db.query(Customer).get(customer_id)
    return templates.TemplateResponse(request, "admin/customers_form.html", {"request": request, "user": user, "customer": customer})


@router.post("/customers/edit/{customer_id}")
def customer_edit(
    customer_id: int,
    name: str = Form(...),
    email: str = Form(None),
    address: str = Form(None),
    city: str = Form(None),
    country: str = Form(None),
    db: Session = Depends(get_db)
):
    customer = db.query(Customer).get(customer_id)
    customer.name = name
    customer.email = email
    customer.address = address
    customer.city = city
    customer.country = country
    db.commit()
    return RedirectResponse(url="/dashboard/customers", status_code=303)


# 🗑️ Kunde löschen
@router.get("/customers/delete/{customer_id}")
def customer_delete(customer_id: int, db: Session = Depends(get_db)):
    c = db.query(Customer).get(customer_id)
    if c:
        db.delete(c)
        db.commit()
    return RedirectResponse(url="/dashboard/customers", status_code=303)


# 📄 Hilfsfunktion: Nächste Rechnungsnummer ermitteln
def get_next_invoice_number(db: Session) -> str:
    last_invoice = db.query(Invoice).order_by(Invoice.id.desc()).first()
    if last_invoice:
        try:
            last_num = int(last_invoice.invoice_number.split("-")[-1])
            return f"{date.today().year}-{last_num + 1:04d}"
        except ValueError:
            return f"{date.today().year}-0001"
    else:
        return f"{date.today().year}-0001"
    
    
# 📄 Rechnungsübersicht
@router.get("/invoices", response_class=HTMLResponse)
def invoices_list(request: Request, db: Session = Depends(get_db)):
    user = require_login(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    # 📌 Professionell: Neueste zuerst + Status optional
    invoices = (
        db.query(Invoice)
        .order_by(Invoice.due_date.desc())
        .all()
    )

    # 📌 Firmenwährung einbinden (falls vorhanden)
    company_settings = db.query(CompanySettings).first()

    return templates.TemplateResponse(
        "admin/invoices.html",
        {
            "request": request,
            "user": user,
            "invoices": invoices,
            "company_settings": company_settings
        }
    )

# ➕ Neue Rechnung erstellen (Formular)
@router.get("/invoices/create", response_class=HTMLResponse)
def invoice_create_form(request: Request, db: Session = Depends(get_db)):
    user = require_login(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    customers = db.query(Customer).all()
    company = db.query(CompanySettings).first()

    # 🔢 Nächste Rechnungsnummer (nur aktuelles Jahr)
    year = date.today().year
    last = (
        db.query(Invoice)
        .filter(Invoice.invoice_number.like(f"{year}-%"))
        .order_by(Invoice.id.desc())
        .first()
    )
    seq = 0
    if last and "-" in last.invoice_number:
        try:
            seq = int(last.invoice_number.split("-")[1])
        except ValueError:
            seq = 0
    next_number = f"{year}-{seq + 1:03d}"

    return templates.TemplateResponse(
        "admin/invoices_create.html",
        {
            "request": request,
            "customers": customers,
            "company": company,
            "next_number": next_number,   # 👉 im Formular vorbelegen
            "user": user,
        },
    )

# 💾 Neue Rechnung speichern + PDF erzeugen + E-Mail versenden
@router.post("/invoices/create")
def invoice_create(
    request: Request,
    background_tasks: BackgroundTasks,             # ✅ für E-Mail-Versand im Hintergrund
    customer_id: int = Form(...),
    invoice_number: str = Form(...),
    total_amount: float = Form(...),
    due_date: date = Form(...),
    tax_rate: float = Form(19.0),
    db: Session = Depends(get_db),
):
    # 🔐 Login prüfen
    user = require_login(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    # 🧮 Betrag berechnen
    net = float(total_amount)
    tax = round(net * (tax_rate / 100.0), 2)
    gross = round(net + tax, 2)

    # 🧾 Rechnung speichern
    invoice = Invoice(
        customer_id=customer_id,
        invoice_number=invoice_number,
        total_amount=gross,
        due_date=due_date,
        date=date.today(),
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    # 🧩 Standardposition hinzufügen (Pauschalbetrag)
    db.add(
        InvoiceItem(
            invoice_id=invoice.id,
            description="Pauschalbetrag",
            quantity=1,
            unit_price=net,
            tax_rate=tax_rate,
        )
    )
    db.commit()

    # 📄 PDF generieren
    customer = db.query(Customer).get(customer_id)
    company = db.query(CompanySettings).first()
    pdf_path = generate_invoice_pdf(invoice, invoice.items, customer, company)

    # ✉️ E-Mail-Versand vorbereiten (läuft im Hintergrund)
    background_tasks.add_task(
        send_invoice_email,
        recipient=customer.email,
        subject=f"🧾 Ihre Rechnung {invoice_number}",
        pdf_path=pdf_path,
        customer_name=customer.name
    )

    # ✅ zurück zur Übersicht
    return RedirectResponse(url="/dashboard/invoices", status_code=303)

    # 📌 Optional: Standardposition anlegen (Pauschalbetrag)

    db.add(InvoiceItem(
        invoice_id=invoice.id,
        description="Pauschalbetrag",
        quantity=1,
        unit_price=total_with_tax,  # bereits inkl. MwSt.
        tax_rate=0
    ))
    db.commit()

    return RedirectResponse(url="/dashboard/invoices", status_code=303)


# ✏️ Rechnung bearbeiten
@router.get("/invoices/edit/{invoice_id}", response_class=HTMLResponse)
def invoice_edit_form(invoice_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_login(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    invoice = db.query(Invoice).get(invoice_id)
    customers = db.query(Customer).all()
    company = db.query(CompanySettings).first()
    return templates.TemplateResponse(
        "admin/invoices_edit.html",
        {"request": request, "invoice": invoice, "customers": customers, "company": company, "user": user}
    )


@router.post("/invoices/edit/{invoice_id}")
def invoice_edit(
    invoice_id: int,
    customer_id: int = Form(...),
    invoice_number: str = Form(...),
    total_amount: float = Form(...),
    due_date: date = Form(...),
    status: str = Form(...),
    db: Session = Depends(get_db)
):
    inv = db.query(Invoice).get(invoice_id)
    inv.customer_id = customer_id
    inv.invoice_number = invoice_number
    inv.total_amount = total_amount
    inv.due_date = due_date
    inv.status = status
    db.commit()
    return RedirectResponse(url="/dashboard/invoices", status_code=303)


# ➕ Rechnungsposition hinzufügen
@router.post("/invoices/items/add/{invoice_id}")
def add_invoice_item(
    invoice_id: int,
    description: str = Form(...),
    quantity: int = Form(...),
    unit_price: float = Form(...),
    tax_rate: float = Form(...),
    db: Session = Depends(get_db)
):
    item = InvoiceItem(invoice_id=invoice_id, description=description, quantity=quantity, unit_price=unit_price, tax_rate=tax_rate)
    db.add(item)
    db.commit()
    invoice = db.query(Invoice).get(invoice_id)
    invoice.total_amount = sum([(i.quantity * i.unit_price) * (1 + i.tax_rate / 100) for i in invoice.items])
    db.commit()
    return RedirectResponse(url=f"/dashboard/invoices/edit/{invoice_id}", status_code=303)


# 🗑️ Rechnungsposition löschen
@router.get("/invoices/items/delete/{item_id}/{invoice_id}")
def delete_invoice_item(item_id: int, invoice_id: int, db: Session = Depends(get_db)):
    item = db.query(InvoiceItem).get(item_id)
    if item:
        db.delete(item)
        db.commit()
    invoice = db.query(Invoice).get(invoice_id)
    invoice.total_amount = sum([(i.quantity * i.unit_price) for i in invoice.items])
    db.commit()
    return RedirectResponse(url=f"/dashboard/invoices/edit/{invoice_id}", status_code=303)

# 🧾 PDF erzeugen
@router.get("/invoices/pdf/{invoice_id}")
def invoice_pdf(invoice_id: int, db: Session = Depends(get_db)):
    # ✅ 1. Rechnung laden
    invoice = db.query(Invoice).get(invoice_id)
    if not invoice:
        return RedirectResponse(url="/dashboard/invoices", status_code=303)

    # ✅ 2. Kunde, Positionen, Firmeninfos laden
    customer = db.query(Customer).get(invoice.customer_id)
    company  = db.query(CompanySettings).first()     # ⬅️ Firmendaten
    items    = invoice.items

    # ✅ 3. PDF generieren (Funktion akzeptiert 4 Parameter)
    pdf_path = generate_invoice_pdf(invoice, items, customer, company)

    # ✅ 4. PDF als Download zurückgeben
    return FileResponse(
        pdf_path,
        filename=f"Rechnung_{invoice.invoice_number}.pdf",
        media_type="application/pdf"
    )
# 🏢 Firmeninfos bearbeiten
@router.get("/company", response_class=HTMLResponse)
def company_settings_form(request: Request, db: Session = Depends(get_db)):
    user = require_login(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    settings = db.query(CompanySettings).first()
    return templates.TemplateResponse(request, "admin/company_settings.html", {"request": request, "settings": settings})

# 🏢 Firmeninfos speichern (inkl. Währung & Logo)
@router.post("/company")
def save_company_settings(
    company_name: str = Form(...),
    address: str = Form(None),
    city: str = Form(None),
    country: str = Form(None),
    email: str = Form(None),
    phone: str = Form(None),
    iban: str = Form(None),
    bic: str = Form(None),
    vat_number: str = Form(None),
    legal_notice: str = Form(None),
    enable_sepa: bool = Form(False),
    enable_twint: bool = Form(False),
    enable_online_payment: bool = Form(False),
    currency_code: str = Form("EUR"),              # 🆕 Währungscode z. B. EUR, CHF, USD
    logo: UploadFile = None,
    db: Session = Depends(get_db)
):
    # ✅ Bestehende Einstellungen laden oder neu anlegen
    settings = db.query(CompanySettings).first() or CompanySettings()

    # 📋 Allgemeine Firmendaten speichern
    settings.company_name = company_name
    settings.address = address
    settings.city = city
    settings.country = country
    settings.email = email
    settings.phone = phone
    settings.iban = iban
    settings.bic = bic
    settings.vat_number = vat_number
    settings.legal_notice = legal_notice

    # 💳 Zahlungsarten speichern
    settings.enable_sepa = enable_sepa
    settings.enable_twint = enable_twint
    settings.enable_online_payment = enable_online_payment

    # 🌍 Währung speichern
    settings.currency_code = (currency_code or "EUR").upper()

    # 🖼 Logo Upload sicher durchführen
    if logo and logo.filename:
        upload_path = Path("app/static/uploads")
        upload_path.mkdir(parents=True, exist_ok=True)

        safe_filename = Path(logo.filename).name  # Sicherheitsmaßnahme gegen Pfad-Tricks
        file_path = upload_path / safe_filename

        # 🧹 Optional: altes Logo löschen
        if settings.logo_path:
            old_logo = Path("app") / settings.logo_path.lstrip("/")
            if old_logo.exists():
                old_logo.unlink()

        with open(file_path, "wb") as f:
            f.write(logo.file.read())

        settings.logo_path = f"/static/uploads/{safe_filename}"

    # 💾 In DB speichern
    db.add(settings)
    db.commit()

    return RedirectResponse(url="/dashboard/company", status_code=303)




@router.get("/bank-import", response_class=HTMLResponse)
def bank_import_form(request: Request):
    return templates.TemplateResponse(
        "admin/bank_import.html",
        {"request": request}
    )


@router.post("/bank-import", response_class=HTMLResponse)
async def bank_import_upload(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # 📂 Temporäre Datei speichern
    upload_path = f"/tmp/{file.filename}"
    with open(upload_path, "wb") as buffer:
        buffer.write(await file.read())

    # 📊 CAMT-Datei einlesen
    payments = parse_camt053(upload_path)

    matched, unmatched = [], []

    # 🔍 Rechnungsabgleich
    for p in payments:
        if p["type"] != "CRDT":
            continue  # nur Gutschriften relevant

        # 🔹 Versuche, per Referenz die Rechnung zu finden (z. B. RF2025-010 oder Nummer direkt)
        invoice = db.query(Invoice).filter(
            Invoice.invoice_number == p["reference"]
        ).first()

        if invoice and float(invoice.total_amount) == float(p["amount"]):
            invoice.status = InvoiceStatus.paid
            db.commit()
            matched.append(invoice.invoice_number)
        else:
            unmatched.append(p)

    return templates.TemplateResponse(
        "admin/bank_import.html",
        {
            "request": request,
            "matched": matched,
            "unmatched": unmatched
        }
    )
    
    
    # 📄 Überfällige Rechnungen anzeigen
@router.get("/invoices/overdue", response_class=HTMLResponse)
def overdue_invoices(request: Request, db: Session = Depends(get_db)):
    user = require_login(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    overdue = db.query(Invoice).filter(
        Invoice.due_date < date.today(),
        Invoice.status.in_([InvoiceStatus.sent, InvoiceStatus.reminder])
    ).all()

    return templates.TemplateResponse(
        "admin/invoices_overdue.html",
        {"request": request, "user": user, "invoices": overdue}
    )


# 📄 Mahnungen anzeigen
@router.get("/invoices/reminders", response_class=HTMLResponse)
def reminder_invoices(request: Request, db: Session = Depends(get_db)):
    user = require_login(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    reminders = db.query(Invoice).filter(
        Invoice.reminder_level > 0
    ).order_by(Invoice.due_date.asc()).all()

    return templates.TemplateResponse(
        "reminders.html",   # ✅ neues Template
        {"request": request, "user": user, "reminders": reminders}  # ✅ Variable richtig benennen
    )