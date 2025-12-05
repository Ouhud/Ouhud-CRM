# app/company.py

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional, List
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
    prefix="/dashboard/company_accounts",
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

    # Optional: Permissions
    require_role(current_user, ["admin", "mitarbeiter", "support"])

    companies: List[CustomerCompany] = (
        db.query(CustomerCompany)
        .order_by(CustomerCompany.name.asc())
        .all()
    )

    contacts: List[Customer] = (
        db.query(Customer)
        .order_by(Customer.first_name.asc())
        .all()
    )

    return templates.TemplateResponse(
        "dashboard/company_contacts.html",
        {
            "request": request,
            "user": current_user,        # 🔥 WICHTIG für Sidebar / Avatar
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
    address: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    country: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    website: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    require_role(current_user, ["admin", "mitarbeiter"])

    if db.query(CustomerCompany).filter_by(name=name).first():
        raise HTTPException(400, "Firma existiert bereits")

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

    log_action(db, current_user.id, f"Firma '{name}' erstellt")

    return RedirectResponse("/dashboard/company_accounts", status_code=303)


# -------------------------------------------------------
# 3) Kontakt anlegen
# -------------------------------------------------------
@router.post("/create_contact")
def create_contact(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    phone: Optional[str] = Form(None),
    position: Optional[str] = Form(None),
    company_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    require_role(current_user, ["admin", "mitarbeiter"])

    if db.query(Customer).filter_by(email=email).first():
        raise HTTPException(400, "Kontakt mit dieser E-Mail existiert bereits")

    full_name = f"{first_name} {last_name}"

    contact = Customer(
        first_name=first_name,
        last_name=last_name,
        name=full_name,
        email=email,
        phone=phone,
        position=position,
        company_id=company_id
    )

    db.add(contact)
    db.commit()

    log_action(db, current_user.id, f"Kontakt '{full_name}' erstellt")

    return RedirectResponse("/dashboard/company_accounts", status_code=303)