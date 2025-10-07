# app/payments.py
from datetime import date
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Payment, Invoice, PaymentStatus, User, Role
from app.auth import get_current_user, require_login
from app.permissions import require_role

router = APIRouter(
    prefix="/dashboard/payments",
    tags=["Zahlungen"]
)


# 📌 Liste aller Zahlungen
@router.get("/", response_class=HTMLResponse)
def list_payments(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login)
):
    from main import templates   # ✅ Lazy import

    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    # 🧭 Rechteprüfung (Admin oder Mitarbeiter)
    if current_user.role.name not in ["admin", "mitarbeiter"]:
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    payments = db.query(Payment).order_by(Payment.date.desc()).all()

    return templates.TemplateResponse(
        "dashboard/payments_list.html",
        {"request": request, "payments": payments}
    )


# ➕ Zahlung erfassen
@router.post("/create")
def create_payment(
    invoice_id: int,
    amount: float,
    date_: date,
    method: str,
    note: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login)
):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    if current_user.role.name not in ["admin", "mitarbeiter"]:
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    invoice = db.query(Invoice).get(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")

    payment = Payment(
        invoice_id=invoice_id,
        amount=amount,
        date=date_,
        method=method,
        note=note,
        status=PaymentStatus.received
    )
    db.add(payment)
    db.commit()
    return RedirectResponse("/dashboard/payments", status_code=303)


# ➕ Formularseite: Neue Zahlung erfassen
@router.get("/new", response_class=HTMLResponse)
def new_payment_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login)
):
    from main import templates

    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    if current_user.role.name not in ["admin", "mitarbeiter"]:
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    invoices = db.query(Invoice).all()  # Liste der Rechnungen für Auswahlfeld

    return templates.TemplateResponse(
        "dashboard/payment_new.html",
        {"request": request, "invoices": invoices}
    )