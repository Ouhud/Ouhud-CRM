# app/utils/logging_utils.py

from sqlalchemy.orm import Session
from app.models import ActivityLog

def log_action(db: Session, user_id: int | None, action: str) -> None:
    """
    📝 Speichert eine Aktion im Aktivitätslog.
    - user_id: ID des ausführenden Benutzers (None möglich für Systemaktionen)
    - action: Beschreibung der Aktion (z. B. 'Kunde erstellt')
    """
    log_entry = ActivityLog(user_id=user_id, action=action)
    db.add(log_entry)
    db.commit()