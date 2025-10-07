# app/customers.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, ConfigDict
from typing import List, Optional
from sqlalchemy.exc import IntegrityError




# 🧭 Projekt-Module
from app.database import get_db
from app.auth import get_current_user
from app.permissions import require_role
from app.models import User, Role, Customer   # ✅ User statt 
from app.utils.logging_utils import log_action

# 📌 Router für Kundenverwaltung
router = APIRouter(
    prefix="/customers",
    tags=["Kundenverwaltung"]
)


# 📝 Pydantic-Schemas
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

    # ✅ Neue Konfiguration für Pydantic v2
    model_config = ConfigDict(from_attributes=True)
    
    
# 📋 Alle Kunden abrufen (🔐 geschützt)
@router.get("/", response_model=List[CustomerOut])
def get_customers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Customer).all()


# 🧾 Einzelnen Kunden anzeigen (🔐 geschützt)
@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")
    return customer


# ➕ Neuen Kunden anlegen (nur Admin oder Mitarbeiter) + Logging
@router.post("/", response_model=CustomerOut)
def create_customer(
    customer: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    require_role(current_user, ["admin", "mitarbeiter"])  # ✅ angepasst

    db_customer = Customer(
        name=customer.name,
        email=customer.email,
        phone=customer.phone,
        address=customer.address,
        city=customer.city,
        country=customer.country
    )

    try:
        db.add(db_customer)
        db.commit()
        db.refresh(db_customer)

        log_action(db, current_user.id, f"Kunde '{customer.name}' erstellt")
        return db_customer

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="E-Mail-Adresse existiert bereits")


# ✏️ Kunden aktualisieren (nur Admin oder Mitarbeiter) + Logging
@router.put("/{customer_id}", response_model=CustomerOut)
def update_customer(
    customer_id: int,
    updated: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    require_role(current_user, ["admin", "mitarbeiter"])  # ✅ angepasst

    db_customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not db_customer:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")

    db_customer.name = updated.name
    db_customer.email = updated.email
    db_customer.phone = updated.phone
    db_customer.address = updated.address
    db_customer.city = updated.city
    db_customer.country = updated.country

    try:
        db.commit()
        db.refresh(db_customer)
        log_action(db, current_user.id, f"Kunde '{updated.name}' aktualisiert")
        return db_customer

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="E-Mail-Adresse existiert bereits")


# 🗑 Kunden löschen (nur Admin) + Logging
@router.delete("/{customer_id}")
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    require_role(current_user, ["admin"])  # ✅ angepasst

    db_customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not db_customer:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")

    db.delete(db_customer)
    db.commit()

    log_action(db, current_user.id, f"Kunde '{db_customer.name}' gelöscht")
    return {"message": f"Kunde mit ID {customer_id} wurde gelöscht"}