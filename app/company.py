# app/company.py

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from fastapi.templating import Jinja2Templates

from app.database import get_db
from app.auth import get_current_user
from app.permissions import require_role
from app.models import CustomerCompany, Customer, User
from app.utils.logging_utils import log_action


templates = Jinja2Templates(directory="templates")


# -------------------------------------------------------
# Router
# -------------------------------------------------------
router = APIRouter(
    prefix="/dashboard/company_accounts",   # NEUE CRM-SEITE
    tags=["Dashboard – Firmen & Kontakte"]
)


# -------------------------------------------------------
# 1) Firmen & Kontakte Dashboard
# -------------------------------------------------------
@router.get("/")
def dashboard_company_home(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    companies = db.query(CustomerCompany).all()
    contacts = db.query(Customer).all()

    return templates.TemplateResponse(
        "dashboard/company_contacts.html",   # WICHTIG: richtiger Pfad!
        {
            "request": request,
            "companies": companies,
            "contacts": contacts
        }
    )


# -------------------------------------------------------
# 2) Firma anlegen
# -------------------------------------------------------
@router.post("/create")
def create_company(
    request: Request,
    name: str = Form(...),
    address: str = Form(None),
    city: str = Form(None),
    country: str = Form(None),
    phone: str = Form(None),
    email: str = Form(None),
    website: str = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    require_role(current_user, ["admin", "mitarbeiter"])

    company = CustomerCompany(
        name=name,
        address=address,
        city=city,
        country=country,
        phone=phone,
        email=email,
        website=website
    )

    db.add(company)
    db.commit()
    db.refresh(company)

    log_action(db, current_user.id, f"Firma '{name}' erstellt")

    # ✔ RICHTIGER Redirect
    return RedirectResponse(
    "/dashboard/company_accounts",
    status_code=303
)

# -------------------------------------------------------
# 3) Kontakt anlegen
# -------------------------------------------------------
@router.post("/create_contact")
def create_contact(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(None),
    position: str = Form(None),
    company_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    require_role(current_user, ["admin", "mitarbeiter"])

    contact = Customer(
        first_name=first_name,
        last_name=last_name,
        name=f"{first_name} {last_name}",
        email=email,
        phone=phone,
        position=position,
        company_id=company_id if company_id else None
    )

    db.add(contact)
    db.commit()
    db.refresh(contact)

    log_action(db, current_user.id, f"Kontakt '{contact.name}' erstellt")

    # ✔ RICHTIGER Redirect
    return RedirectResponse(
        "/dashboard/company_accounts",
        status_code=303
    )