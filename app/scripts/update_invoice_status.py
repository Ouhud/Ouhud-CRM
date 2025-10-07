# app/scripts/update_invoice_status.py
from datetime import date, timedelta
from app.models import Invoice, InvoiceStatus
from app.database import SessionLocal

def run():
    db = SessionLocal()

    try:
        # 📌 Alle offenen Rechnungen abrufen, die fällig sind
        overdue_invoices = db.query(Invoice).filter(
            Invoice.status == InvoiceStatus.sent,
            Invoice.due_date < date.today()
        ).all()

        for inv in overdue_invoices:
            # 1. Mahnung, falls noch keine versendet wurde
            if inv.reminder_level == 0:
                inv.reminder_level = 1
                inv.status = InvoiceStatus.reminder
                print(f"📨 Erste Mahnung für Rechnung {inv.invoice_number} gesetzt.")
            else:
                # Bereits gemahnt, dann auf "überfällig" setzen
                inv.status = InvoiceStatus.overdue
                print(f"⚠️ Rechnung {inv.invoice_number} ist überfällig (Mahnstufe {inv.reminder_level}).")

        db.commit()

    finally:
        db.close()

if __name__ == "__main__":
    run()

