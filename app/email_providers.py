# ---------------------------------------------------
# E-Mail Provider Verwaltung (Professionelle Version)
# Ouhud CRM – by Hamza Mehmalat
# ---------------------------------------------------

from fastapi import (
    APIRouter, Request, Depends, Form, HTTPException
)
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.permissions import require_role
from app.models import EmailProvider, EmailLog, CustomerCompany, User
from app.email_sender import send_test_email
from app.utils.logging_utils import log_action

router = APIRouter(
    prefix="/dashboard/email",
    tags=["E-Mail Provider Verwaltung"]
)

templates = Jinja2Templates(directory="templates")


# ---------------------------------------------------
# 1) LISTE ALLER PROVIDER + ANSICHT
# ---------------------------------------------------
@router.get("/")
def list_providers(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    company = db.query(CustomerCompany).first()
    if not company:
        raise HTTPException(500, "Keine Firma konfiguriert.")

    providers = db.query(EmailProvider).filter(
        EmailProvider.customer_company_id == company.id
    ).order_by(EmailProvider.created_at.desc()).all()

    return templates.TemplateResponse(
        "email/settings.html",
        {
            "request": request,
            "user": current_user,    # ← FIX !!!
            "company": company,
            "providers": providers
        }
    )


# ---------------------------------------------------
# 2) PROVIDER SPEICHERN
# ---------------------------------------------------
@router.post("/save")
def save_provider(
    request: Request,
    provider: str = Form(...),

    # SMTP
    smtp_host: str = Form(None),
    smtp_port: int = Form(None),
    smtp_user: str = Form(None),
    smtp_password: str = Form(None),

    # SendGrid
    sendgrid_key: str = Form(None),

    # Mailgun
    mailgun_key: str = Form(None),

    # SES
    ses_key: str = Form(None),
    ses_secret: str = Form(None),
    ses_region: str = Form(None),

    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    require_role(current_user, ["admin"])

    company = db.query(CustomerCompany).first()
    if not company:
        raise HTTPException(500, "Keine Firma konfiguriert.")

    new_provider = EmailProvider(
        customer_company_id=company.id,  # <── FIX
        provider=provider,

        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_user=smtp_user,
        smtp_password=smtp_password,

        sendgrid_key=sendgrid_key,
        mailgun_key=mailgun_key,

        ses_key=ses_key,
        ses_secret=ses_secret,
        ses_region=ses_region,

        is_active=False
    )

    db.add(new_provider)
    db.commit()

    log_action(db, current_user.id, f"E-Mail Provider hinzugefügt: {provider}")

    return RedirectResponse("/dashboard/email", status_code=303)


# ---------------------------------------------------
# 3) AKTIVEN PROVIDER UMSCHALTEN
# ---------------------------------------------------
@router.get("/{provider_id}/activate")
def activate_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    require_role(current_user, ["admin"])

    company = db.query(CustomerCompany).first()
    if not company:
        raise HTTPException(500, "Keine Firma konfiguriert.")

    # Alles deaktivieren
    db.query(EmailProvider).filter(
        EmailProvider.customer_company_id == company.id  # <── FIX
    ).update({"is_active": 0})

    # Ausgewählten aktivieren
    provider = db.query(EmailProvider).filter(
        EmailProvider.id == provider_id,
        EmailProvider.customer_company_id == company.id  # <── FIX
    ).first()

    if not provider:
        raise HTTPException(404, "Provider nicht gefunden.")

    provider.is_active = True
    db.commit()

    log_action(db, current_user.id, f"E-Mail Provider aktiviert: {provider.provider}")

    return RedirectResponse("/dashboard/email", status_code=303)


# ---------------------------------------------------
# 4) TEST E-MAIL SENDEN
# ---------------------------------------------------
@router.post("/test")
def test_provider_email(
    request: Request,
    to_email: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    company = db.query(CustomerCompany).first()
    if not company:
        raise HTTPException(500, "Keine Firma konfiguriert.")

    provider = db.query(EmailProvider).filter(
        EmailProvider.customer_company_id == company.id,  # <── FIX
        EmailProvider.is_active == True
    ).first()

    if not provider:
        raise HTTPException(400, "Kein aktiver Provider konfiguriert.")

    success, message = send_test_email(provider, to_email)

    # Logging
    log = EmailLog(
        customer_company_id=company.id,  # <── FIX
        provider_id=provider.id,
        to_email=to_email,               # FIX Feldname
        subject="Test-E-Mail",
        status="success" if success else "failed",
        error_message=None if success else message
    )
    db.add(log)
    db.commit()

    log_action(
        db,
        current_user.id,
        f"Test E-Mail gesendet → {to_email} ({'OK' if success else 'ERROR'})"
    )

    return RedirectResponse("/dashboard/email", status_code=303)


# ---------------------------------------------------
# 5) COMPOSE (E-Mail erstellen)
# ---------------------------------------------------
@router.get("/compose")
def compose_email(request: Request,
                  db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("email/compose.html", {
        "request": request,
        "user": current_user,
        "active_tab": "compose"
    })


# ---------------------------------------------------
# 6) E-Mail LOGS
# ---------------------------------------------------
@router.get("/logs")
def email_logs(request: Request,
               db: Session = Depends(get_db),
               current_user: User = Depends(get_current_user)):

    company = db.query(CustomerCompany).first()

    logs = db.query(EmailLog).filter(
        EmailLog.customer_company_id == company.id  # <── FIX
    ).order_by(EmailLog.created_at.desc()).all()

    return templates.TemplateResponse("email/logs.html", {
    "request": request,
    "user": current_user,
    "logs": logs,
    "active_tab": "logs"
})