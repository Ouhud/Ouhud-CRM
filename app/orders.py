# app/orders.py
import os
from datetime import datetime

from fastapi import (
    APIRouter,
    Request,
    Depends,
    Form,
    HTTPException
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import require_login
from app.models import OrderDB, Customer

# 📂 Templates-Ordner ermitteln
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# 📌 Router definieren
router = APIRouter(prefix="/dashboard", tags=["Orders"])


# ============================================================
# 📄 GET: Bestellübersicht anzeigen
# ============================================================
@router.get("/orders", response_class=HTMLResponse)
def orders_page(
    request: Request,
    db: Session = Depends(get_db)
):
    """Zeigt eine Liste aller Bestellungen an."""
    user = request.state.user
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    orders = db.query(OrderDB).order_by(OrderDB.order_date.desc()).all()
    customers = db.query(Customer).all()

    return templates.TemplateResponse(
        "dashboard/orders.html",
        {
            "request": request,
            "user": user,
            "orders": orders,
            "customers": customers
        }
    )


# ============================================================
# 📝 POST: Neue Bestellung anlegen
# ============================================================
@router.post("/orders/create")
def create_order(
    request: Request,
    customer_id: int = Form(...),
    total_amount: float = Form(...),
    status: str = Form("offen"),
    db: Session = Depends(get_db)
):
    """Erstellt eine neue Bestellung."""
    user = request.state.user
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")

    order = OrderDB(
        customer_id=customer_id,
        total_amount=total_amount,
        status=status,
        order_date=datetime.utcnow()
    )
    db.add(order)
    db.commit()

    return RedirectResponse(url="/dashboard/orders?created=1", status_code=303)


# ============================================================
# 🗑 POST: Bestellung löschen
# ============================================================
@router.post("/orders/{order_id}/delete")
def delete_order(
    order_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Löscht eine bestehende Bestellung."""
    user = request.state.user
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    order = db.query(OrderDB).filter(OrderDB.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Bestellung nicht gefunden")

    db.delete(order)
    db.commit()

    return RedirectResponse(url="/dashboard/orders?deleted=1", status_code=303)