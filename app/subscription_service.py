from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models import Subscription


# ------------------------------------------------------------
# KONSTANTEN
# ------------------------------------------------------------
TRIAL_DAYS = 14
FREE_MONTHS = 3

PLAN_LIMITS = {
    "basic": 3,
    "pro": 15,
    "professional": 999
}

PLANS = ["basic", "pro", "professional"]


# ------------------------------------------------------------
# 1) Neue Subscription erstellen
# ------------------------------------------------------------
def create_subscription(db: Session, company_id: int, plan: str, billing_cycle: str):

    if plan not in PLANS:
        raise ValueError("Ungültiger Plan")

    if billing_cycle not in ["monthly", "yearly"]:
        raise ValueError("Ungültiger Abrechnungszyklus")

    now = datetime.utcnow()

    subscription = Subscription(
        company_id=company_id,
        plan=plan,
        billing_cycle=billing_cycle,
        start_date=now,

        # Testphase
        trial_end=now + timedelta(days=TRIAL_DAYS),

        # Wird erst aktiviert NACH Trial
        free_months_end=None,
        next_payment=None,

        status="trial",
        user_limit=PLAN_LIMITS[plan],
    )

    db.add(subscription)
    db.commit()
    db.refresh(subscription)

    return subscription


# ------------------------------------------------------------
# 2) Benutzerlimit bestimmen
# ------------------------------------------------------------
def get_user_limit(plan: str):
    return PLAN_LIMITS.get(plan, 1)


# ------------------------------------------------------------
# 3) Nach Testphase → kostenlose Monate starten
# ------------------------------------------------------------
def activate_free_months(db: Session, subscription: Subscription):
    now = datetime.utcnow()

    subscription.free_months_end = now + timedelta(days=FREE_MONTHS * 30)
    subscription.status = "active"
    subscription.next_payment = subscription.free_months_end

    db.commit()
    db.refresh(subscription)

    return subscription


# ------------------------------------------------------------
# 4) Nächste Zahlung berechnen
# ------------------------------------------------------------
def calculate_next_payment(subscription: Subscription):

    if subscription.billing_cycle == "monthly":
        return datetime.utcnow() + timedelta(days=30)

    if subscription.billing_cycle == "yearly":
        return datetime.utcnow() + timedelta(days=365)

    return None


# ------------------------------------------------------------
# 5) Kostenpflichtige Phase startet
# ------------------------------------------------------------
def activate_paid_subscription(db: Session, subscription: Subscription):

    subscription.status = "active"
    subscription.next_payment = calculate_next_payment(subscription)

    db.commit()
    db.refresh(subscription)

    return subscription


# ------------------------------------------------------------
# 6) Upgrade / Downgrade
# ------------------------------------------------------------
def change_plan(db: Session, subscription: Subscription, new_plan: str):

    if new_plan not in PLANS:
        raise ValueError("Ungültiger Plan")

    old_plan = subscription.plan
    subscription.last_plan = old_plan
    subscription.plan = new_plan
    subscription.user_limit = PLAN_LIMITS[new_plan]
    subscription.upgraded_at = datetime.utcnow()

    # Wenn Plan geändert → Rechnung neu berechnen
    if new_plan != old_plan:
        subscription.next_payment = calculate_next_payment(subscription)

    db.commit()
    db.refresh(subscription)

    return subscription


# ------------------------------------------------------------
# 7) Subscription kündigen
# ------------------------------------------------------------
def cancel_subscription(db: Session, subscription: Subscription):
    subscription.status = "canceled"
    subscription.canceled_at = datetime.utcnow()

    db.commit()
    db.refresh(subscription)

    return subscription


# ------------------------------------------------------------
# 8) Automatische Überprüfung (Cron / API)
# ------------------------------------------------------------
def check_subscription_status(db: Session, subscription: Subscription):

    now = datetime.utcnow()

    # Trial > abgelaufen?
    if subscription.status == "trial" and now >= subscription.trial_end:
        return activate_free_months(db, subscription)

    # Free Months > abgelaufen?
    if subscription.free_months_end and now >= subscription.free_months_end:
        return activate_paid_subscription(db, subscription)

    return subscription