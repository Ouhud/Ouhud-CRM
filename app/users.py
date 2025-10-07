# app/users.py
from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import require_login, hash_password

router = APIRouter(
    prefix="/users",
    tags=["Benutzerprofil"]
)

templates = Jinja2Templates(directory="app/templates")


# 👤 Profilseite anzeigen
@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, db: Session = Depends(get_db)):
    user = require_login(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    return templates.TemplateResponse(
        "users/settings.html",
        {"request": request, "current_user": user}
    )


# 🔑 Passwort / E-Mail ändern
@router.post("/settings/update")
def update_settings(
    request: Request,
    email: str = Form(...),
    password: str = Form(None),
    db: Session = Depends(get_db)
):
    user = require_login(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    user.email = email
    if password and password.strip():
        user.hashed_password = hash_password(password)

    db.add(user)
    db.commit()

    return RedirectResponse(url="/users/settings?success=1", status_code=303)