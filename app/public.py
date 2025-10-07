# app/public.py
import secrets
from datetime import date
from fastapi import APIRouter, Form, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Customer, Invoice, InvoiceItem, Product   # ✅ Produktmodell importiert
from app.utils.pdf_utils import generate_invoice_pdf

# 📌 Router für öffentliche Bestellungen (z. B. Shop oder Landingpage)
router = APIRouter(prefix="/public", tags=["Public"])

# 📌 Template-Verzeichnis für öffentliche Seiten
templates = Jinja2Templates(directory="templates")


# 📝 1️⃣ Formular-Seite mit Produktliste anzeigen
@router.get("/order", response_class=HTMLResponse)
def order_form(request: Request, db: Session = Depends(get_db)):
    """
    Öffentliche Bestellseite.
    - Zeigt eine dynamische Liste aktiver Produkte an.
    - Wird oft in Landingpages, Shops oder externen Portalen eingebettet.
    """
    products = db.query(Product).filter(Product.active == True).all()
    return templates.TemplateResponse(
        "public/order_form.html",
        {"request": request, "products": products}
    )


# 🧾 2️⃣ Bestellung absenden & Rechnung automatisch erzeugen
@router.post("/order", response_class=HTMLResponse)
def submit_order(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    product: str = Form(...),
    quantity: int = Form(...),
    db: Session = Depends(get_db)
):
    """
    Öffentliche Bestellung entgegennehmen:
    - Kunde wird automatisch angelegt (falls nicht vorhanden)
    - Produktpreis wird aus DB gelesen
    - Rechnung & Positionen werden erstellt
    - PDF wird generiert
    - Weiterleitung zur Zahlungsseite
    """

    # 🧍 1️⃣ Kunde finden oder neu anlegen
    customer = db.query(Customer).filter_by(email=email).first()
    if not customer:
        customer = Customer(
            name=name,
            email=email,
            country="DE",
            customer_number=f"C-{date.today().year}-{secrets.randbelow(99999):05d}"
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)

    # 🧮 2️⃣ Produktpreis aus DB holen
    product_obj = db.query(Product).filter_by(name=product, active=True).first()
    if not product_obj:
        return templates.TemplateResponse(
            "public/order_form.html",
            {
                "request": request,
                "products": db.query(Product).filter(Product.active == True).all(),
                "error": f"Produkt '{product}' nicht gefunden oder inaktiv."
            },
            status_code=400
        )

    net = product_obj.price
    total = net * quantity
    tax_rate = 19.0  # 📝 Optional: In Zukunft auch produktabhängig machen
    gross = round(total * (1 + tax_rate / 100), 2)

    # 🧾 3️⃣ Rechnung erstellen
    invoice_number = f"{date.today().year}-{secrets.randbelow(9999):04d}"
    invoice = Invoice(
        customer_id=customer.id,
        invoice_number=invoice_number,
        total_amount=gross,
        due_date=date.today(),
        date=date.today(),
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    # 📌 4️⃣ Rechnungsposition hinzufügen
    item = InvoiceItem(
        invoice_id=invoice.id,
        description=product_obj.name,
        quantity=quantity,
        unit_price=net,
        tax_rate=tax_rate
    )
    db.add(item)
    db.commit()

    # 📝 5️⃣ PDF generieren
    try:
        pdf_path = generate_invoice_pdf(invoice, invoice.items, customer, None)
        print(f"✅ PDF erzeugt unter: {pdf_path}")
    except Exception as e:
        print(f"⚠️ PDF-Generierung fehlgeschlagen: {e}")

    # 💳 6️⃣ Weiterleitung zur Zahlungsseite
    return RedirectResponse(url=f"/pay/{invoice_number}", status_code=303)