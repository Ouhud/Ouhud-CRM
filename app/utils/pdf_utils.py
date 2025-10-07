# app/utils/pdf_utils.py
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from pathlib import Path

from app.models import CompanySettings
from app.database import SessionLocal
from app.utils.qrcode_utils import generate_link_qr, generate_sepa_qr, generate_twint_qr


# 🏢 Firmendaten aus DB laden
def get_company_settings():
    db = SessionLocal()
    try:
        return db.query(CompanySettings).first()
    finally:
        db.close()


# 💰 Währungsformatierung (EU-konform)
def fmt_money(val: float, code: str) -> str:
    code = (code or "EUR").upper()
    symbol = {"EUR": "€", "CHF": "CHF", "USD": "$", "GBP": "£"}.get(code, code)
    s = f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if code == "CHF":
        return f"{s} {symbol}"
    return f"{s} {symbol}"


# 📄 DIN-5008 / EU-konforme Rechnungserzeugung
def generate_invoice_pdf(invoice, items, customer, company=None):
    company = company or get_company_settings()
    currency = (company.currency_code or "EUR").upper()

    # 📁 Zielverzeichnis
    out_dir = Path("app/static/invoices")
    out_dir.mkdir(parents=True, exist_ok=True)
    file_path = out_dir / f"invoice_{invoice.invoice_number}.pdf"

    c = canvas.Canvas(str(file_path), pagesize=A4)
    width, height = A4

    # ─────────── Kopfbereich ───────────
    left = 25 * mm
    right = width - 25 * mm
    top = height - 25 * mm

    # Logo (ISO-konforme Größe: ca. 45–50 mm Breite)
    if company and company.logo_path:
        logo_file = Path("app") / company.logo_path.lstrip("/")
        if logo_file.exists():
            c.drawImage(
                str(logo_file),
                right - 50 * mm,   # etwas breiter
                top - 20 * mm,
                width=50 * mm,
                height=18 * mm,
                preserveAspectRatio=True,
                mask="auto"
            )

    # Firmenadresse
    if company:
        y = top - 25 * mm
        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(right, y, company.company_name or "")
        c.setFont("Helvetica", 9)
        for line in filter(None, [
            company.address,
            f"{company.city or ''}, {company.country or ''}",
            company.email,
            company.phone,
        ]):
            y -= 4.5 * mm
            c.drawRightString(right, y, line)

    # Kundendaten & Rechnungsinfo
    y = top - 30 * mm
    c.setFont("Helvetica-Bold", 14)
    c.drawString(left, y, f"Rechnung {invoice.invoice_number}")
    y -= 8 * mm

    c.setFont("Helvetica", 10)
    for line in filter(None, [
        f"Kunde: {customer.name}",
        customer.address,
        f"{customer.city or ''}, {customer.country or ''}",
        f"E-Mail: {getattr(customer, 'email', '')}" if getattr(customer, 'email', None) else None,
        f"Rechnungsdatum: {invoice.date.strftime('%d.%m.%Y')}",
        f"Fällig am: {invoice.due_date.strftime('%d.%m.%Y')}",
    ]):
        c.drawString(left, y, line)
        y -= 5 * mm


    # ─────────── Mahnungsstempel (falls aktiv) ───────────
    if getattr(invoice, "reminder_level", 0) > 0:
        c.setFont("Helvetica-Bold", 16)
        c.setFillColorRGB(0.8, 0, 0)  # Rot
        c.drawString(left, top - 15 * mm, f"{invoice.reminder_level}. Mahnung")
        c.setFillColorRGB(0, 0, 0)  # Schriftfarbe zurücksetzen
        
        
    # ─────────── Positionstabelle ───────────
    y -= 10 * mm
    c.setFont("Helvetica-Bold", 10)

    # 📏 Professionelle Spaltenaufteilung (max. ca. 160 mm nutzbar)
    col_desc  = left                  # Beschreibung
    col_qty   = col_desc + 90 * mm    # Menge
    col_unit  = col_qty + 25 * mm     # Einzelpreis
    col_tax   = col_unit + 25 * mm    # MwSt
    col_total = col_tax + 25 * mm     # Gesamtbetrag

    # Tabellenkopf
    c.drawString(col_desc, y, "Beschreibung")
    c.drawRightString(col_qty, y, "Menge")
    c.drawRightString(col_unit, y, "Einzelpreis")
    c.drawRightString(col_tax, y, "MwSt")
    c.drawRightString(col_total, y, "Gesamt")

    y -= 6 * mm
    c.line(left, y, right, y)
    y -= 8 * mm

    # Tabelleninhalt
    c.setFont("Helvetica", 9)
    total_net, total_tax, total_gross = 0.0, 0.0, 0.0

    for item in items:
        qty = float(getattr(item, "quantity", 1) or 1)
        unit = float(getattr(item, "unit_price", 0.0))
        tax_rate = float(getattr(item, "tax_rate", 0.0))
        net = qty * unit
        tax = round(net * tax_rate / 100, 2)
        gross = round(net + tax, 2)

        total_net += net
        total_tax += tax
        total_gross += gross

        # Zeile zeichnen
        c.drawString(col_desc, y, (item.description or "")[:60])
        c.drawRightString(col_qty, y, f"{int(qty)}")
        c.drawRightString(col_unit, y, fmt_money(unit, currency))
        c.drawRightString(col_tax, y, f"{tax_rate:.0f}")
        c.drawRightString(col_total, y, fmt_money(gross, currency))

        y -= 6 * mm
        if y < 60 * mm:  # Seitenumbruch bei Bedarf
            c.showPage()
            y = top - 25 * mm
            c.setFont("Helvetica", 9)

    # ─────────── Summenblock ───────────
    y -= 10 * mm
    c.setFont("Helvetica-Bold", 10)

    # 🧭 Linke Beschriftung & rechte Werte sauber trennen
    label_x = col_total - 60   # Position der Summenbeschriftungen
    value_x = col_total        # Position der Beträge (rechtsbündig)

    # Zwischensumme Netto
    c.drawRightString(label_x, y, "Zwischensumme (netto):")
    c.drawRightString(value_x, y, fmt_money(total_net, currency))
    y -= 7 * mm

    # MwSt
    c.drawRightString(label_x, y, "MwSt:")
    c.drawRightString(value_x, y, fmt_money(total_tax, currency))
    y -= 7 * mm

    # Gesamtbetrag
    c.drawRightString(label_x, y, "Gesamtbetrag:")
    c.drawRightString(value_x, y, fmt_money(total_gross, currency))
    
    # ─────────── QR-Zahlungsbereich ───────────
    qr_y = 35 * mm
    qr_size = 30 * mm
    x_right = right

    if company and company.enable_online_payment:
        qr = generate_link_qr(f"https://ouhud.com/pay/{invoice.invoice_number}", f"link_{invoice.invoice_number}")
        c.drawImage(qr, x_right - qr_size, qr_y, width=qr_size, height=qr_size)
        c.setFont("Helvetica", 8)
        c.drawRightString(x_right, qr_y - 4, "🌐 Online-Zahlung")
        x_right -= qr_size + 10

    if company and company.enable_sepa and company.iban:
        qr = generate_sepa_qr(
            iban=company.iban,
            name=company.company_name or "Firma",
            amount=total_gross,
            purpose=f"Rechnung {invoice.invoice_number}",
            filename=f"sepa_{invoice.invoice_number}",
        )
        c.drawImage(qr, x_right - qr_size, qr_y, width=qr_size, height=qr_size)
        c.drawRightString(x_right, qr_y - 4, "🇪🇺 SEPA")
        x_right -= qr_size + 10

    if company and company.enable_twint:
        qr = generate_twint_qr(
            iban="CH9300762011623852957",
            reference=f"RF{invoice.invoice_number}",
            amount=total_gross,
            currency=currency,
            filename=f"twint_{invoice.invoice_number}",
        )
        c.drawImage(qr, x_right - qr_size, qr_y, width=qr_size, height=qr_size)
        c.drawRightString(x_right, qr_y - 4, "🇨🇭 TWINT")

        # ─────────── Fußbereich (Bank & Firmendaten) ───────────
    c.setFont("Helvetica", 8)

    # Linie über dem Fußbereich
    c.line(left, 25 * mm, right, 25 * mm)

    footer_y = 20 * mm
    if company:
        lines = [
            f"{company.company_name or ''} • {company.address or ''} • {company.city or ''}, {company.country or ''}",
            f"UID / MwSt.-Nr.: {company.vat_number or '-'}",
            f"IBAN: {company.iban or '-'} • BIC: {company.bic or '-'}",
            f"E-Mail: {company.email or '-'} • Tel: {company.phone or '-'}"
        ]

        for line in lines:
            if line.strip():
                c.drawCentredString(width / 2, footer_y, line)
                footer_y -= 4 * mm

    # Optionaler Dankestext ganz unten
    c.setFont("Helvetica", 7)
    c.drawCentredString(width / 2, 10 * mm, "Vielen Dank für Ihren Auftrag!")
    
    
    
    # 📌 PDF speichern
    c.save()

    # ✅ WICHTIG: Pfad zurückgeben!
    return str(file_path)