# app/products.py
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Product

router = APIRouter(prefix="/dashboard/products", tags=["Dashboard"])

templates = Jinja2Templates(directory="templates")


# 📄 1️⃣ Liste aller Produkte
@router.get("/", response_class=HTMLResponse)
def product_list(request: Request, db: Session = Depends(get_db)):
    products = db.query(Product).all()
    return templates.TemplateResponse(
        request,
        "admin/products.html",
        {"request": request, "products": products}
    )

# ➕ 2️⃣ Neues Produkt erstellen (Formular absenden)
@router.post("/create")
def create_product(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    price: float = Form(...),
    active: bool = Form(True),
    db: Session = Depends(get_db)
):
    product = Product(name=name, description=description, price=price, active=active)
    db.add(product)
    db.commit()
    return RedirectResponse(url="/dashboard/products", status_code=303)


# ✏️ 3️⃣ Produkt bearbeiten (Formular absenden)
@router.post("/edit/{product_id}")
def edit_product(
    product_id: int,
    name: str = Form(...),
    description: str = Form(""),
    price: float = Form(...),
    active: bool = Form(False),
    db: Session = Depends(get_db)
):
    product = db.query(Product).get(product_id)
    if product:
        product.name = name
        product.description = description
        product.price = price
        product.active = active
        db.commit()
    return RedirectResponse(url="/dashboard/products", status_code=303)


# 🗑 4️⃣ Produkt löschen
@router.get("/delete/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).get(product_id)
    if product:
        db.delete(product)
        db.commit()
    return RedirectResponse(url="/dashboard/products", status_code=303)