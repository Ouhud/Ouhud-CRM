from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, ConfigDict
from typing import List, Optional
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.auth import get_current_user
from app.permissions import require_role
from app.models import User, Customer
from app.utils.logging_utils import log_action

router = APIRouter(
    prefix="/customers",
    tags=["Kundenverwaltung"]
)

# Pydantic Schemas
class CustomerBase(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None

class CustomerCreate(CustomerBase):
    pass

class CustomerOut(CustomerBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# GET: Kundenliste
@router.get("/", response_model=List[CustomerOut])
def get_customers(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tenant = request.state.tenant
    return (
        db.query(Customer)
        .filter(Customer.company_id == tenant.id)
        .all()
    )

# GET: Einzelner Kunde
@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(
    customer_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tenant = request.state.tenant

    customer = (
        db.query(Customer)
        .filter(Customer.id == customer_id, Customer.company_id == tenant.id)
        .first()
    )

    if not customer:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")
    return customer

# POST: Neuer Kunde
@router.post("/", response_model=CustomerOut)
def create_customer(
    request: Request,
    customer: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    require_role(current_user, ["admin", "mitarbeiter"])
    tenant = request.state.tenant

    db_customer = Customer(
        name=customer.name,
        email=customer.email,
        phone=customer.phone,
        address=customer.address,
        city=customer.city,
        country=customer.country,
        company_id=tenant.id     # ❗❗ WICHTIG
    )

    try:
        db.add(db_customer)
        db.commit()
        db.refresh(db_customer)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="E-Mail existiert bereits")

    log_action(db, current_user.id, f"Kunde '{customer.name}' erstellt")

    return db_customer

# PUT: Update
@router.put("/{customer_id}", response_model=CustomerOut)
def update_customer(
    customer_id: int,
    updated: CustomerCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    require_role(current_user, ["admin", "mitarbeiter"])
    tenant = request.state.tenant

    db_customer = (
        db.query(Customer)
        .filter(Customer.id == customer_id, Customer.company_id == tenant.id)
        .first()
    )

    if not db_customer:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")

    db_customer.name = updated.name
    db_customer.email = updated.email
    db_customer.phone = updated.phone
    db_customer.address = updated.address
    db_customer.city = updated.city
    db_customer.country = updated.country

    db.commit()
    db.refresh(db_customer)

    log_action(db, current_user.id, f"Kunde '{updated.name}' aktualisiert")
    return db_customer

# DELETE: Kunde löschen
@router.delete("/{customer_id}")
def delete_customer(
    customer_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    require_role(current_user, ["admin"])
    tenant = request.state.tenant

    db_customer = (
        db.query(Customer)
        .filter(Customer.id == customer_id, Customer.company_id == tenant.id)
        .first()
    )

    if not db_customer:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")

    db.delete(db_customer)
    db.commit()

    log_action(db, current_user.id, f"Kunde '{db_customer.name}' gelöscht")
    return {"message": "Kunde gelöscht"}