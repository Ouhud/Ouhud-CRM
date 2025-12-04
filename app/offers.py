# app/offers.py

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.auth import get_current_user
from app.permissions import require_role
from app.models import Offer, Customer, User
from app.utils.logging_utils import log_action

templates = Jinja2Templates(directory="templates")

router = APIRouter(
    prefix="/dashboard/offers",
    tags=["Angebote"]
)


# --------------------------------------------------------
# LISTE ALLER ANGEBOTE  +  Formular anzeigen
# --------------------------------------------------------
@router.get("/")
def list_offers(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    offers = db.query(Offer).order_by(Offer.created_at.desc()).all()
    customers = db.query(Customer).all()

    return templates.TemplateResponse(
        "dashboard/offers.html",
        {
            "request": request,
            "mode": "list",
            "offers": offers,
            "customers": customers
        }
    )


# --------------------------------------------------------
# ERSTELLEN (FORMULAR)
# --------------------------------------------------------
@router.get("/create")
def form_create_offer(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    customers = db.query(Customer).all()

    return templates.TemplateResponse(
        "dashboard/offers.html",
        {
            "request": request,
            "mode": "create",
            "customers": customers
        }
    )


# --------------------------------------------------------
# ERSTELLEN (POST)
# --------------------------------------------------------
@router.post("/create")
def create_offer(
    request: Request,
    title: str = Form(...),
    description: Optional[str] = Form(None),
    amount: float = Form(...),
    customer_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    require_role(current_user, ["admin", "mitarbeiter"])

    offer = Offer(
        title=title,
        description=description,
        amount=amount,
        customer_id=customer_id
    )

    db.add(offer)
    db.commit()
    db.refresh(offer)

    log_action(db, current_user.id, f"Angebot '{title}' erstellt")
    return RedirectResponse("/dashboard/offers", status_code=303)


# --------------------------------------------------------
# ANGEBOT ANZEIGEN
# --------------------------------------------------------
@router.get("/{offer_id}")
def view_offer(
    request: Request,
    offer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(404, "Angebot nicht gefunden")

    return templates.TemplateResponse(
        "dashboard/offers.html",
        {
            "request": request,
            "mode": "view",
            "offer": offer
        }
    )


# --------------------------------------------------------
# BEARBEITEN (FORMULAR)
# --------------------------------------------------------
@router.get("/{offer_id}/edit")
def edit_offer_form(
    request: Request,
    offer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    customers = db.query(Customer).all()

    if not offer:
        raise HTTPException(404, "Angebot nicht gefunden")

    return templates.TemplateResponse(
        "dashboard/offers.html",
        {
            "request": request,
            "mode": "edit",
            "offer": offer,
            "customers": customers
        }
    )


# --------------------------------------------------------
# BEARBEITEN (POST)
# --------------------------------------------------------
@router.post("/{offer_id}/edit")
def edit_offer(
    request: Request,
    offer_id: int,
    title: str = Form(...),
    description: Optional[str] = Form(None),
    amount: float = Form(...),
    customer_id: int = Form(...),
    status: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(404, "Angebot nicht gefunden")

    offer.title = title
    offer.description = description
    offer.amount = amount
    offer.customer_id = customer_id
    offer.status = status

    db.commit()

    log_action(db, current_user.id, f"Angebot '{title}' aktualisiert")
    return RedirectResponse(f"/dashboard/offers/{offer_id}", status_code=303)


# --------------------------------------------------------
# LÖSCHEN
# --------------------------------------------------------
@router.get("/{offer_id}/delete")
def delete_offer(
    offer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(404, "Angebot nicht gefunden")

    db.delete(offer)
    db.commit()

    log_action(db, current_user.id, f"Angebot gelöscht: ID {offer_id}")
    return RedirectResponse("/dashboard/offers", status_code=303)