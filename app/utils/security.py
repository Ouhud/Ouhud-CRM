# app/utils/security.py

from passlib.context import CryptContext
from fastapi import Request, HTTPException
from starlette.responses import RedirectResponse

# 🔐 Passwort-Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# 🧭 Login-Check für geschützte Routen
def require_login(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Bitte zuerst einloggen.")
    return user