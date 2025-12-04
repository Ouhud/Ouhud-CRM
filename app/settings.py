# app/settings.py
import os
from fastapi import (
    APIRouter,
    Request,
    Depends,
    Form,
    HTTPException,
    status
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import require_login, hash_password
from app.models import User  # ✅ UserDB → User (neues Modell verwenden)

# 📁 Templates-Ordner ermitteln (plattformunabhängig)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# 🌐 Router definieren
router = APIRouter(prefix="/dashboard", tags=["Einstellungen"])


# ============================================================
# 🧭 GET: Einstellungen-Seite anzeigen
# ============================================================
@router.get("/settings", response_class=HTMLResponse)
def settings_page(
    request: Request,
    db: Session = Depends(get_db)
):
    """Zeigt die Benutzereinstellungen an."""
    user = request.state.user
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    return templates.TemplateResponse(
        "dashboard/settings.html",
        {
            "request": request,
            "current_user": user
        }
    )


# ============================================================
# 📝 POST: Benutzereinstellungen aktualisieren
# ============================================================
@router.post("/settings/update")
def update_settings(
    request: Request,
    email: str = Form(...),
    password: str = Form(None),
    language: str = Form("de"),
    db: Session = Depends(get_db)
):
    """
    Aktualisiert E-Mail, Passwort und optionale Sprache 
    des aktuell eingeloggten Benutzers.
    """
    user = request.state.user
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    # 📧 E-Mail aktualisieren
    user.email = email

    # 🔑 Passwort ändern, wenn angegeben
    if password and password.strip():
        user.hashed_password = hash_password(password)

    # 🌐 Sprache speichern (optional)
    # Wenn du später Mehrsprachigkeit brauchst, kannst du hier eine Spalte `language` hinzufügen.
    # user.language = language

    db.add(user)
    db.commit()

    # Erfolgreich zurück
    return RedirectResponse(url="/dashboard/settings?success=1", status_code=303)


# ============================================================
# 🚨 POST: Benutzerkonto löschen
# ============================================================
@router.post("/settings/delete-account")
def delete_account(
    request: Request,
    db: Session = Depends(get_db)
):
    """Löscht das Benutzerkonto unwiderruflich."""
    user = request.state.user
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    db.delete(user)
    db.commit()

    # Cookie löschen & Redirect zur Loginseite
    response = RedirectResponse(url="/auth/login", status_code=303)
    response.delete_cookie("access_token")
    return response