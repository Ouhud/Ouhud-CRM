# app/auth.py
import os
from datetime import datetime, timedelta
from fastapi import (
    APIRouter, Depends, HTTPException, status, Form, Request
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_




import secrets
from app.utils.email_utils import send_password_reset_email  # 📧 musst du anlegen



from fastapi import Query
from typing import Optional
from fastapi import Cookie, Security
from app.models import PasswordResetToken
import uuid

from app.database import get_db
from app.models import User, Role

# -------------------- 🔐 JWT KONFIGURATION --------------------
SECRET_KEY = os.getenv("SECRET_KEY", "supergeheim")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)

# -------------------- 🧭 ROUTER + TEMPLATES --------------------
router = APIRouter(prefix="/auth", tags=["Authentication"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# -------------------- 🧰 HILFSFUNKTIONEN --------------------
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def authenticate_user(db: Session, username_or_email: str, password: str):
    """Benutzer mit Benutzername ODER E-Mail authentifizieren."""
    user = db.query(User).filter(
        or_(User.username == username_or_email, User.email == username_or_email)
    ).first()

    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

# -------------------- 🌐 ROUTEN --------------------

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str = None):
    error_message = None
    if error == "1":
        error_message = "❌ Benutzername oder Passwort ist falsch."
    return templates.TemplateResponse(
        request,
        "auth/login.html",
        {"request": request, "error_message": error_message}
    )

# 🪄 API-Login (POST, Token für API-Clients)
@router.post("/token")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falscher Benutzername oder Passwort",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(data={"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}


# 🌐 Web-Login (POST, Formular)
@router.post("/login")
def login_web(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    # 🧍 Benutzer authentifizieren
    user = authenticate_user(db, username, password)
    if not user:
        # ❌ Wenn Benutzername oder Passwort falsch ist → zurück zum Login mit Fehler
        return RedirectResponse(url="/auth/login?error=1", status_code=303)

    # 🔐 JWT-Token erzeugen
    token = create_access_token(data={"sub": user.username})

    # 🧭 Nach erfolgreichem Login zum Dashboard weiterleiten
    response = RedirectResponse(url="/dashboard/", status_code=303)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True
    )
    return response

# -------------------- 👤 Aktueller Benutzer aus Cookie --------------------
def get_current_user(
    db: Session = Depends(get_db),
    access_token: str = Cookie(default=None)
):
    """
    Holt den eingeloggten Benutzer anhand des Cookies 'access_token'.
    Wird typischerweise für API-Endpunkte genutzt.
    """
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nicht eingeloggt"
        )

    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Ungültiger Token"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token-Fehler"
        )

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Benutzer nicht gefunden"
        )

    return user


# -------------------- 🔐 Login-Prüfung für Template-Seiten --------------------
def require_login(request: Request, db: Session = Depends(get_db)):
    """
    Stellt sicher, dass ein Benutzer eingeloggt ist.
    Wird als Dependency für geschützte HTML-Seiten verwendet.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nicht eingeloggt"
        )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Ungültiger Token"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token-Fehler"
        )

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Benutzer nicht gefunden"
        )

    return user


# -------------------- 📝 Registrierung --------------------
@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(request, "auth/register.html", {"request": request})


@router.post("/register")
def register_user(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form("user"),   # Standardrolle
    db: Session = Depends(get_db)
):
    # Rolle validieren
    role_obj = db.query(Role).filter(Role.name == role).first()
    if not role_obj:
        raise HTTPException(status_code=400, detail="Ungültige Rolle.")

    hashed_pw = hash_password(password)
    new_user = User(
        username=username,
        email=email,
        hashed_password=hashed_pw,
        role_id=role_obj.id
    )
    db.add(new_user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Benutzername oder E-Mail bereits vorhanden.")

    token = create_access_token(data={"sub": username})
    response = RedirectResponse(url="/dashboard/", status_code=303)
    response.set_cookie(key="access_token", value=token, httponly=True)
    return response


# -------------------- 🚪 Logout --------------------
@router.get("/logout")
def logout():
    response = RedirectResponse(url="/auth/login", status_code=303)
    response.delete_cookie("access_token")
    return response

# -------------------- 🔑 Passwort vergessen & zurücksetzen (NEU) --------------------


@router.get("/forgot", response_class=HTMLResponse)
def forgot_password_form(request: Request):
    """
    Zeigt Formular zum Anfordern eines Passwort-Reset-Links.
    """
    return templates.TemplateResponse(request, "auth/forgot.html", {"request": request})


@router.post("/forgot")
def forgot_password_submit(email: str = Form(...), db: Session = Depends(get_db)):
    """
    Erstellt einen Reset-Token und sendet den Link per E-Mail (oder Log).
    """
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Wir geben absichtlich immer dieselbe Antwort, um Nutzer nicht zu verraten
        return RedirectResponse(url="/auth/login?reset_sent=1", status_code=303)

    # 🧭 Token erzeugen & speichern
    token = str(uuid.uuid4())
    reset_token = PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(hours=1)
    )
    db.add(reset_token)
    db.commit()

    # 📬 Reset-Link generieren (später per SMTP verschicken)
    reset_link = f"http://127.0.0.1:8000/auth/reset-password?token={token}"
    print(f"📧 Passwort-Reset-Link für {user.email}: {reset_link}")

    # Optional: send_password_reset_email(user.email, reset_link)
    return RedirectResponse(url="/auth/login?reset_sent=1", status_code=303)


@router.get("/reset-password", response_class=HTMLResponse)
def reset_password_form(request: Request, token: str = Query(...), db: Session = Depends(get_db)):
    """
    Zeigt das Formular zum Eingeben eines neuen Passworts, wenn Token gültig.
    """
    token_obj = db.query(PasswordResetToken).filter(PasswordResetToken.token == token).first()
    if not token_obj or token_obj.expires_at < datetime.utcnow():
        return templates.TemplateResponse(
            request,
            "auth/reset_password.html",
            {"request": request, "error": "Ungültiger oder abgelaufener Token."}
        )
    return templates.TemplateResponse(
        request,
        "auth/reset_password.html",
        {"request": request, "token": token}
    )


@router.post("/reset-password")
def reset_password_submit(
    request: Request,
    token: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Setzt ein neues Passwort, wenn der Token gültig ist, und löscht den Token danach.
    """
    token_obj = db.query(PasswordResetToken).filter(PasswordResetToken.token == token).first()
    if not token_obj or token_obj.expires_at < datetime.utcnow():
        return templates.TemplateResponse(
            request,
            "auth/reset_password.html",
            {"request": request, "error": "Ungültiger oder abgelaufener Token."}
        )

    user = db.query(User).filter(User.id == token_obj.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="Benutzer nicht gefunden")

    # 🔐 Passwort prüfen & speichern
    if len(password) < 8:
        return templates.TemplateResponse(
            request,
            "auth/reset_password.html",
            {"request": request, "token": token, "error": "Passwort muss mindestens 8 Zeichen lang sein."}
        )

    user.hashed_password = hash_password(password)
    db.delete(token_obj)  # Token unbrauchbar machen
    db.commit()

    return RedirectResponse(url="/auth/login?reset_success=1", status_code=303)



# -------------------- 🛡️ Admin-Zugriff --------------------
from fastapi import Depends

def require_admin(user: User = Depends(get_current_user)):
    """
    Gewährleistet, dass der aktuelle Benutzer die Rolle 'admin' hat.
    Diese Funktion kann als Dependency für geschützte Admin-Routen genutzt werden.
    """
    if not user or not user.role or user.role.name != "admin":
        raise HTTPException(
            status_code=403,
            detail="Nur Administratoren haben Zugriff auf diesen Bereich."
        )
    return user