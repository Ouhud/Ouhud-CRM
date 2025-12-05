# app/dashboard_users.py

import os
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Role
from app.auth import get_current_user, require_admin

router = APIRouter(prefix="/dashboard/users", tags=["Benutzerverwaltung"])

# 📌 Templates-Verzeichnis korrekt auflösen
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


# ============================================================
# 📋 Benutzerliste anzeigen (Admin)
# ============================================================
@router.get("/", response_class=HTMLResponse)
def list_users(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Nicht eingeloggt → Login
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    # Nur Admin
    if not current_user.role or current_user.role.name != "admin":
        return RedirectResponse(url="/dashboard/", status_code=303)

    # Benutzer + Rollen laden
    users = db.query(User).all()
    roles = db.query(Role).all()

    return templates.TemplateResponse(
    "admin/users.html",
    {
        "request": request,
        "user": current_user,   #  🔥 WICHTIG!
        "users": users,
        "roles": roles,
    },
)


# ============================================================
# ✏️ Benutzer-Rolle ändern (nur Admin)
# ============================================================
@router.post("/edit-role")
def edit_role(
    request: Request,
    user_id: int = Form(...),
    role_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Auth prüfen
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    # Admin prüfen
    if not current_user.role or current_user.role.name != "admin":
        return RedirectResponse(url="/dashboard/", status_code=303)

    # Rolle ändern
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        new_role = db.query(Role).filter(Role.id == role_id).first()
        if new_role:
            user.role = new_role
            db.commit()

    return RedirectResponse(url="/dashboard/users", status_code=303)