# app/auth_utils.py

from typing import Optional
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from fastapi import Request

from app.database import SessionLocal
from app.models import User
from app.auth import SECRET_KEY, ALGORITHM


async def get_user_from_token(token: str) -> Optional[User]:
    """
    Holt Benutzer aus JWT-Token.
    Öffnet eigene DB-Session.
    Sicher & universell nutzbar für Middleware.
    """
    if not token:
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            return None
    except JWTError:
        return None

    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        return user
    finally:
        db.close()


def attach_user_to_request(request: Request, user: Optional[User]):
    """
    Speichert Benutzer-Objekt im Request-State.
    Wird vom Middleware genutzt.
    """
    request.state.user = user