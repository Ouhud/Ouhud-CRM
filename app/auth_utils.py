# app/auth_utils.py

from typing import Optional, Dict, Any
from jose import jwt, JWTError
from sqlalchemy.orm import Session, joinedload
from fastapi import Request

from app.database import SessionLocal
from app.models import User
from app.auth import SECRET_KEY, ALGORITHM


# ---------------------------
# Benutzer aus Token laden
# ---------------------------
async def get_user_from_token(token: str) -> Optional[User]:
    """
    Holt Benutzer aus JWT-Token.
    Öffnet eigene DB-Session.
    Enthält bereits joinedload() für Rolle.
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
        user = (
            db.query(User)
            .options(joinedload(User.role))
            .filter(User.username == username)
            .first()
        )
        return user
    finally:
        db.close()


# ---------------------------
# Benutzer im Request speichern
# ---------------------------
def attach_user_to_request(request: Request, user: Optional[User]) -> None:
    request.state.user


# ---------------------------
# User → Serializable dict
# ---------------------------
def serialize_user(u: Optional[User]) -> Optional[Dict[str, Any]]:
    """
    User ORM-Objekt in reines Dictionary konvertieren.
    Wird sicher in Templates verwendet.
    """
    if u is None:
        return None

    return {
        "id": int(u.id),
        "username": str(u.username),
        "email": str(u.email),
        "avatar_url": getattr(u, "avatar_url", None),
        "status": getattr(u, "status", "online"),
        "role": u.role.name if u.role else "admin",
    }