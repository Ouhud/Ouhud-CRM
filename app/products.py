# app/products.py

from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.auth import get_current_user
from app.permissions import require_role
from app.models import Product, User, Category       # ✔ korrekt – EIN Import!
from app.utils.logging_utils import log_action
from app.utils.template_utils import render_template


router = APIRouter(
    prefix="/dashboard/products",
    tags=["Dashboard – Produkte"]
)


# ---------------------------------------------------------
# 1️⃣ PRODUKT-LISTE
# ---------------------------------------------------------
@router.get("/")
def product_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    require_role(current_user, ["admin", "mitarbeiter"])

    products = db.query(Product).order_by(Product.id.desc()).all()
    categories = db.query(Category).all()

    return render_template(
        request,
        "admin/products.html",
        {
            "products": products,
            "categories": categories
        }
    )


# ---------------------------------------------------------
# 2️⃣ PRODUKT ANLEGEN (POST)
# ---------------------------------------------------------
@router.post("/create")
def create_product(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    price: float = Form(...),
    category_id: Optional[int] = Form(None),     # ✔ Kategorie hinzufügen
    active: Optional[bool] = Form(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    require_role(current_user, ["admin"])

    product = Product(
        name=name,
        description=description,
        price=price,
        category_id=category_id,                 # ✔ speichern
        active=bool(active)
    )

    db.add(product)
    db.commit()

    log_action(db, current_user.id, f"Produkt erstellt: {name}")

    return RedirectResponse(
        "/dashboard/products",
        status_code=303
    )


# ---------------------------------------------------------
# 3️⃣ PRODUKT BEARBEITEN (POST)
# ---------------------------------------------------------
@router.post("/edit/{product_id}")
def edit_product(
    request: Request,
    product_id: int,
    name: str = Form(...),
    description: str = Form(""),
    price: float = Form(...),
    category_id: Optional[int] = Form(None),     # ✔ Kategorie im Form
    active: Optional[bool] = Form(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    require_role(current_user, ["admin", "mitarbeiter"])

    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(404, "Produkt nicht gefunden")

    product.name = name
    product.description = description
    product.price = price
    product.category_id = category_id            # ✔ speichern
    product.active = bool(active)

    db.commit()

    log_action(db, current_user.id, f"Produkt aktualisiert: {name}")

    return RedirectResponse(
        "/dashboard/products",
        status_code=303
    )


# ---------------------------------------------------------
# 4️⃣ PRODUKT LÖSCHEN
# ---------------------------------------------------------
@router.get("/delete/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    require_role(current_user, ["admin"])

    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(404, "Produkt nicht gefunden")

    db.delete(product)
    db.commit()

    log_action(db, current_user.id, f"Produkt gelöscht: ID {product_id}")

    return RedirectResponse(
        "/dashboard/products",
        status_code=303
    )