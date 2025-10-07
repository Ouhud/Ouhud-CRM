# app/permissions.py

from fastapi import HTTPException, status, Depends
from app.models import User
from app.auth import get_current_user

def require_role(*allowed_roles: str):
    """
    🔐 Dependency-Funktion:
    Prüft, ob der aktuelle Benutzer eine der erlaubten Rollen hat.
    Beispiel:
    @router.get("/admin", dependencies=[Depends(require_role("admin"))])
    """
    def dependency(user: User = Depends(get_current_user)):
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Nicht eingeloggt oder Sitzung abgelaufen."
            )

        user_role_name = user.role.name if user.role else None
        if user_role_name not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Zugriff verweigert: Rolle '{user_role_name}' nicht erlaubt."
            )
        return user
    return dependency