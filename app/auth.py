# app/auth.py
import os
from datetime import datetime, timedelta
from fastapi import (
    APIRouter, Depends, HTTPException, status, Form, Request
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session, joinedload
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_

from fastapi import Query, Cookie
from typing import Optional
import uuid

from app.database import get_db
from app.models import User, Role, Company, PasswordResetToken


# ===============================
# 🔐 JWT KONFIGURATION
# ===============================
SECRET_KEY = os.getenv("SECRET_KEY", "supergeheim")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)

# ===============================
# 🔧 ROUTER + TEMPLATES
# ===============================
router = APIRouter(prefix="/auth", tags=["Authentication"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


# ===============================
# 🔧 Hilfsfunktionen
# ===============================
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def authenticate_user(db: Session, username_or_email: str, password: str) -> Optional[User]:
    user = db.query(User).filter(
        or_(User.username == username_or_email, User.email == username_or_email)
    ).first()

    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user


# ===============================
# 🌐 Login-Seite GET
# ===============================
@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str = None):
    error_message = "❌ Benutzername oder Passwort ist falsch." if error == "1" else None
    return templates.TemplateResponse(
        "auth/login.html",
        {"request": request, "error_message": error_message}
    )


@router.get("/", response_class=HTMLResponse)
def auth_home(request: Request, error: str = None):
    error_message = "❌ Benutzername oder Passwort ist falsch." if error == "1" else None
    return templates.TemplateResponse(
        "auth/login.html",
        {"request": request, "error_message": error_message}
    )


# ===============================
# 🧪 API-Login (Token)
# ===============================
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


# ===============================
# 🌐 Login POST (Web)
# ===============================
@router.post("/login")
def login_web(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, username, password)
    if not user:
        return RedirectResponse(url="/auth/?error=1", status_code=303)

    token = create_access_token(data={"sub": user.username})

    response = RedirectResponse(url="/dashboard/", status_code=303)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=60 * 60 * 24 * 7
    )
    return response


# ===============================
# 👤 Aktueller Benutzer – stabil + EAGER ROLE LOAD
# ===============================
def get_current_user(
    db: Session = Depends(get_db),
    access_token: str = Cookie(default=None)
):
    if not access_token:
        return None

    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            return None
    except JWTError:
        return None

    # WICHTIG: Rolle eager laden → verhindert DetachedInstanceError
    return db.query(User).options(joinedload(User.role)).filter(User.username == username).first()


# ===============================
# 🔐 require_login – für HTML Seiten
# ===============================
def require_login(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            return None
    except JWTError:
        return None

    return db.query(User).options(joinedload(User.role)).filter(User.username == username).first()


# ===============================
# 📝 Registrierung
# ===============================
@router.post("/register", response_class=HTMLResponse)
def register_user(
    request: Request,
    company_name: str = Form(...),
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    clean = company_name.lower().replace(" ", "")
    subdomain = "".join(c for c in clean if c.isalnum())

    # Subdomain prüfen
    existing_company = db.query(Company).filter(Company.subdomain == subdomain).first()
    if existing_company:
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error_message": "❌ Diese Firma existiert bereits."}
        )

    # Firma anlegen
    company = Company(
        name=company_name,
        subdomain=subdomain,
        owner_email=email,
        plan="pro",
        status="active"
    )
    db.add(company)
    db.commit()
    db.refresh(company)

    # Admin-Rolle anlegen
    role_admin = Role(name="admin", company_id=company.id)
    db.add(role_admin)
    db.commit()

    # Benutzer anlegen
    new_user = User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
        company_id=company.id,
        role_id=role_admin.id,
        is_active=True
    )

    try:
        db.add(new_user)
        db.commit()
    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error_message": "❌ Benutzername oder E-Mail existiert bereits."}
        )

    # Weiterleiten
    token = create_access_token(data={"sub": new_user.username})
    resp = RedirectResponse(url="/dashboard/", status_code=303)
    resp.set_cookie("access_token", token, httponly=True)
    return resp


# ===============================
# 🚪 Logout
# ===============================
@router.get("/logout")
def logout():
    resp = RedirectResponse(url="/auth/login", status_code=303)
    resp.delete_cookie("access_token")
    return resp


# ===============================
# 🔑 Passwort vergessen
# ===============================
@router.get("/forgot", response_class=HTMLResponse)
def forgot_password_form(request: Request):
    return templates.TemplateResponse("auth/forgot.html", {"request": request})


@router.post("/forgot")
def forgot_password_submit(email: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()

    token = None
    if user:
        token = str(uuid.uuid4())
        reset = PasswordResetToken(
            user_id=user.id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        db.add(reset)
        db.commit()

        print("🔗 Reset-Link:", f"http://127.0.0.1:8000/auth/reset-password?token={token}")

    return RedirectResponse(url="/auth/login?reset_sent=1", status_code=303)


# ===============================
# 🔁 Passwort zurücksetzen
# ===============================
@router.get("/reset-password", response_class=HTMLResponse)
def reset_password_form(request: Request, token: str = Query(...), db: Session = Depends(get_db)):
    token_obj = db.query(PasswordResetToken).filter(PasswordResetToken.token == token).first()

    if not token_obj or token_obj.expires_at < datetime.utcnow():
        return templates.TemplateResponse(
            "auth/reset_password.html",
            {"request": request, "error": "Ungültiger oder abgelaufener Token."}
        )

    return templates.TemplateResponse("auth/reset_password.html", {"request": request, "token": token})


@router.post("/reset-password")
def reset_password_submit(
    request: Request,
    token: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    token_obj = db.query(PasswordResetToken).filter(PasswordResetToken.token == token).first()

    if not token_obj or token_obj.expires_at < datetime.utcnow():
        return templates.TemplateResponse(
            "auth/reset_password.html",
            {"request": request, "error": "Ungültiger oder abgelaufener Token."}
        )

    if len(password) < 8:
        return templates.TemplateResponse(
            "auth/reset_password.html",
            {"request": request, "token": token, "error": "Passwort zu kurz."}
        )

    user = db.query(User).filter(User.id == token_obj.user_id).first()
    user.hashed_password = hash_password(password)

    db.delete(token_obj)
    db.commit()

    return RedirectResponse(url="/auth/login?reset_success=1", status_code=303)


# ===============================
# 🛡️ Admin Prüfung – jetzt stabil
# ===============================
def require_admin(user: User = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=403, detail="Nicht eingeloggt.")
    if not user.role:
        raise HTTPException(status_code=403, detail="Keine Rolle zugewiesen.")
    if user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Nur für Administratoren.")
    return user