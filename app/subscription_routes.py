# app/subscription_routes.py

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models import Subscription
from app.subscription_service import (
    create_subscription,
    change_plan,
    cancel_subscription,
    check_subscription_status
)
from app.auth import get_current_user

from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="templates")

# Router Namespace
router = APIRouter(prefix="/dashboard/subscription")


# ------------------------------------------------------------
# 1) Übersicht – zeigt Abo, Status, Plan, Trial, etc.
# ------------------------------------------------------------
@router.get("/")
def subscription_overview(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    company = current_user.company

    # Aktives oder letztes Subscription holen
    subscription = (
        db.query(Subscription)
        .filter(Subscription.company_id == company.id)
        .order_by(Subscription.id.desc())
        .first()
    )

    # Automatische Prüfung (Trial → Free Months → Paid)
    if subscription:
        check_subscription_status(db, subscription)

    return templates.TemplateResponse(
        "subscription/overview.html",
        {
            "request": request,
            "company": company,
            "subscription": subscription,
            "active_tab": "subscription",
        }
    )


# ------------------------------------------------------------
# 2) Planwechsel Basic → Pro → Professional
# ------------------------------------------------------------
@router.post("/change-plan")
def change_plan_route(
    request: Request,
    plan: str = Form(...),    # basic / pro / professional
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    subscription = (
        db.query(Subscription)
        .filter(Subscription.company_id == current_user.company.id)
        .first()
    )

    if not subscription:
        return RedirectResponse("/dashboard/subscription", status_code=303)

    # Plan ändern
    change_plan(db, subscription, plan)

    return RedirectResponse("/dashboard/subscription", status_code=303)


# ------------------------------------------------------------
# 3) Start Trial – wenn eine Firma neu ist
# ------------------------------------------------------------
@router.post("/start-trial")
def start_trial(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    company = current_user.company

    exists = (
        db.query(Subscription)
        .filter(Subscription.company_id == company.id)
        .first()
    )

    # Wenn nichts existiert → Basisplan + Trial erstellen
    if not exists:
        create_subscription(
            db=db,
            company_id=company.id,
            plan="basic",
            billing_cycle="monthly"
        )

    return RedirectResponse("/dashboard/subscription", status_code=303)


# ------------------------------------------------------------
# 4) Kündigen – Subscription endet
# ------------------------------------------------------------
@router.post("/cancel")
def cancel_subscription_route(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    subscription = (
        db.query(Subscription)
        .filter(Subscription.company_id == current_user.company.id)
        .first()
    )

    if subscription:
        cancel_subscription(db, subscription)

    return RedirectResponse("/dashboard/subscription", status_code=303)