# create_admin.py

from app.database import SessionLocal
from app.models import , UserRole
from app.auth import hash_password

def create_admin():
    db = SessionLocal()
    username = "admin@example.com"
    password = "123456"   # ✅ kannst du später ändern

    # 👀 Prüfen, ob Benutzer schon existiert
    existing_user = db.query().filter_by(username=username).first()
    if existing_user:
        print(f"⚠️ Benutzer '{username}' existiert bereits.")
        db.close()
        return

    # 📝 Neuen Admin-Benutzer erstellen
    admin_user = (
        username=username,
        email=username,
        hashed_password=hash_password(password),
        role=UserRole.admin,
        is_active=True
    )

    db.add(admin_user)
    db.commit()
    db.close()

    print(f"✅ Admin-Benutzer '{username}' erfolgreich angelegt!")
    print(f"🔑 Login mit Passwort: {password}")

if __name__ == "__main__":
    create_admin()

