# app/scripts/import_camt.py

import re
from pathlib import Path
from datetime import datetime
from lxml import etree

from app.database import SessionLocal
from app.models import Invoice, InvoiceStatus, PaymentLog

# 📂 Verzeichnis mit CAMT.053-Dateien (z. B. über SFTP abgelegt)
INCOMING_DIR = Path("app/bank_statements/incoming")

# 🧠 Regex: unterstützt z. B. "2025-0001", "RE-2025-1234", "INV-2025-0002"
INVOICE_REF_PATTERN = re.compile(
    r'(\b\d{4}-\d{4,}\b|\bRE-\d{4}-\d+\b|\bINV-\d{4}-\d+\b)',
    re.IGNORECASE
)


def parse_camt_file(file_path: Path):
    """
    Parst eine camt.053 Datei und extrahiert Zahlungen als Tupel:
    (Rechnungsnummer, Betrag, Buchungsdatum).
    """
    ns = {"ns": "urn:iso:std:iso:20022:tech:xsd:camt.053.001.02"}
    tree = etree.parse(str(file_path))

    payments = []
    for entry in tree.xpath("//ns:Ntry", namespaces=ns):
        # 💰 Betrag extrahieren
        amount_nodes = entry.xpath("./ns:Amt/text()", namespaces=ns)
        if not amount_nodes:
            continue
        try:
            amount = float(amount_nodes[0])
        except ValueError:
            print(f"⚠️ Ungültiger Betrag in {file_path.name}: {amount_nodes[0]}")
            continue

        # 📅 Buchungsdatum auslesen (oder heute, falls nicht vorhanden)
        booking_date_nodes = entry.xpath("./ns:BookgDt/ns:Dt/text()", namespaces=ns)
        booking_date = booking_date_nodes[0] if booking_date_nodes else datetime.today().date().isoformat()

        # 📝 Textquellen: Verwendungszweck + Zusatzinfo
        text_candidates = entry.xpath(".//ns:RmtInf//text()", namespaces=ns) + \
                          entry.xpath(".//ns:AddtlNtryInf/text()", namespaces=ns)
        ref_text = " ".join([t.strip() for t in text_candidates if t.strip()])

        # 🧠 Rechnungsnummer aus Text parsen
        match = INVOICE_REF_PATTERN.search(ref_text)
        if match:
            invoice_number = match.group(1)
            payments.append((invoice_number, amount, booking_date))
        else:
            print(f"⚠️ Keine Rechnungsnummer gefunden in Verwendungszweck: {ref_text}")

    return payments


def mark_invoices_as_paid(payments):
    """
    Markiert passende Rechnungen in der DB als bezahlt,
    speichert das Buchungsdatum 📅 und erstellt einen Logeintrag 📝.
    Auch bei bereits bezahlten Rechnungen wird ein Zahlungseintrag erzeugt.
    """
    db = SessionLocal()
    try:
        for invoice_number, amount, booking_date in payments:
            invoice = (
                db.query(Invoice)
                .filter(Invoice.invoice_number == invoice_number)
                .first()
            )

            if not invoice:
                print(f"⚠️ Keine passende Rechnung für Nummer: {invoice_number}")
                continue

            # 📌 Status aktualisieren, falls noch nicht bezahlt
            if invoice.status != InvoiceStatus.paid:
                invoice.status = InvoiceStatus.paid
                invoice.last_reminder_date = booking_date
                print(f"✅ Rechnung {invoice.invoice_number} als bezahlt markiert.")

            else:
                print(f"ℹ️ Rechnung {invoice.invoice_number} war bereits bezahlt.")

            # 📝 Zahlung protokollieren (immer!)
            log = PaymentLog(
                invoice_id=invoice.id,
                amount=amount,
                booking_date=booking_date,
                message=f"Zahlungseingang am {booking_date}"
            )
            db.add(log)
            db.commit()

            print(f"💰 Zahlung für {invoice.invoice_number} erfasst ({amount:.2f} EUR) am {booking_date}")

    except Exception as e:
        db.rollback()
        print(f"❌ Fehler bei der Zahlungsverbuchung: {e}")
    finally:
        db.close()


def run():
    """
    Läuft über alle XML-Dateien im Incoming-Ordner und verbucht Zahlungen.
    """
    for file in INCOMING_DIR.glob("*.xml"):
        print(f"📄 Verarbeite Datei: {file.name}")
        payments = parse_camt_file(file)

        if payments:
            mark_invoices_as_paid(payments)
        else:
            print(f"⚠️ Keine Zahlungen in {file.name} gefunden.")


if __name__ == "__main__":
    run()