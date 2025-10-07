# app/admin.py
import os
from datetime import datetime
from typing import List


from sqlalchemy import func
from app.models import Customer, Invoice

from fastapi import (
    APIRouter, Depends, Form, HTTPException, Request, status
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

# 🔐 Auth & DB
from app.database import get_db
from app.models import User, Role, ActivityLog
from app.auth import get_current_user, hash_password
from app.permissions import require_role  # Zugriffskontrolle Admin

# ============================================================
# 🧭 Router & Templates
# ============================================================
router = APIRouter(
    prefix="/admin",
    tags=["Administration"]
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


# ============================================================
# 🏠 Admin Dashboard
# ============================================================


router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    """
    Übersicht für Administratoren mit Statistiken über Kunden & Rechnungen.
    """
    customers_count = db.query(func.count(Customer.id)).scalar()
    invoices_count = db.query(func.count(Invoice.id)).scalar()
    total_sum = db.query(func.coalesce(func.sum(Invoice.total_amount), 0)).scalar()

    overdue_count = db.query(func.count(Invoice.id)).filter(
        Invoice.due_date < func.current_date(),
        Invoice.status != "paid"
    ).scalar()

    # ⚠ Reminder-Feld entfernt — wir nutzen Mahnstufen direkt aus invoices
    reminders_count = db.query(func.count(Invoice.id)).filter(
        Invoice.reminder_level > 0
    ).scalar()

    stats = {
        "customers": customers_count or 0,
        "invoices": invoices_count or 0,
        "total_sum": float(total_sum or 0),
        "overdue": overdue_count or 0,
        "reminders": reminders_count or 0,
    }

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {"request": request, "stats": stats}
    )
# ============================================================
# 👥 Benutzerverwaltung – Übersicht
# ============================================================
@router.get("/users/manage", response_class=HTMLResponse)
def manage_users(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Zeigt Benutzerliste & Formular zum Anlegen neuer Benutzer."""
    require_role(current_user, ["admin"])

    users = db.query(User).all()
    roles = db.query(Role).all()

    return templates.TemplateResponse(
        "admin/users.html",
        {"request": request, "users": users, "roles": roles, "current_user": current_user}
    )


# ============================================================
# ➕ Benutzer erstellen (komplett)
# ============================================================
@router.post("/users/create")
def create_user(
    vorname: str = Form(...),
    nachname: str = Form(...),
    email: str = Form(...),
    telefon: str = Form(None),
    adresse: str = Form(None),
    password: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    require_role(current_user, ["admin"])

    # 🔍 E-Mail prüfen
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="E-Mail existiert bereits")

    # 🧭 Rolle suchen
    role_obj = db.query(Role).filter(Role.name == role).first()
    if not role_obj:
        raise HTTPException(status_code=400, detail="Ungültige Rolle")

    # 🆕 Benutzer anlegen
    new_user = User(
        username=email,
        email=email,
        first_name=vorname,
        last_name=nachname,
        phone=telefon,
        address=adresse,
        hashed_password=hash_password(password),
        role_id=role_obj.id,
        created_at=datetime.utcnow(),
        is_active=True
    )
    db.add(new_user)
    db.commit()

    # 📝 Aktivitätslog
    db.add(ActivityLog(
        user_id=current_user.id,
        category="Admin",
        action="Benutzer erstellt",
        details=f"{vorname} {nachname} ({role})"
    ))
    db.commit()

    return RedirectResponse("/admin/users/manage", status_code=303)

# ============================================================
# ✏ Benutzerrolle ändern
# ============================================================
@router.post("/users/{user_id}/role")
def change_user_role(
    user_id: int,
    role: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    require_role(current_user, ["admin"])

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")

    role_obj = db.query(Role).filter(Role.name == role).first()
    if not role_obj:
        raise HTTPException(status_code=400, detail="Ungültige Rolle")

    user.role = role_obj
    db.commit()

    db.add(ActivityLog(
        user_id=current_user.id,
        category="Admin",
        action="Rolle geändert",
        details=f"{user.username} → {role}"
    ))
    db.commit()

    return RedirectResponse("/admin/users/manage", status_code=303)


# ============================================================
# 🗑 Benutzer löschen
# ============================================================
@router.post("/users/{user_id}/delete")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    require_role(current_user, ["admin"])

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")

    db.delete(user)
    db.commit()

    db.add(ActivityLog(
        user_id=current_user.id,
        category="Admin",
        action="Benutzer gelöscht",
        details=f"{user.username} (ID {user_id})"
    ))
    db.commit()

    return RedirectResponse("/admin/users/manage", status_code=303)


# ============================================================
# 📡 API: Benutzerliste (JSON)
# ============================================================
class UserOut(BaseModel):
    id: int
    username: str
    email: str | None
    role: str | None

    model_config = ConfigDict(from_attributes=True)


@router.get("/users", response_model=List[UserOut])
def list_users_api(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    require_role(current_user, ["admin"])
    return db.query(User).all()


# ============================================================
# 👤 Admin Profil anzeigen (z. B. Firmeninfos / Admininfos)
# ============================================================
@router.get("/profile", response_class=HTMLResponse)
def admin_profile(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    require_role(current_user, ["admin"])
    return templates.TemplateResponse(
        "admin/profile.html",
        {"request": request, "user": current_user}
    )