# main.py
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import RedirectResponse
from app import audit
from app import ai_assistant
from app import ai_settings




# 📌 Importiere deine Routen sauber, ohne Dopplungen
from app import (
    auth,
    dashboard,
    dashboard_users,
    users,
    customers,
    admin,
    invoices,
    payments,
    public,
    products,
    reports,
    settings,
    orders,
    leads,
    history,
    calendar,
    integrations,
    campaigns,
    segments,
    reminders,
    chat,
    channels_whatsapp,
    inbox,
    privacy,
    public_payment,
    forms,
)

# 📞 Spezielle Channels separat
from app.channels_calls import router as calls_router

# 🛢️ Datenbank initialisieren
from app.database import init_db

# ─────────────────────────────
# 🧭 Templates global
# ─────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")  # ✅ korrigiert
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# ─────────────────────────────
# 🚀 FastAPI App erstellen
# ─────────────────────────────
app = FastAPI(
    title="Ouhud CRM",
    description="Professionelles CRM-System für Rechnungs- und Kundenverwaltung",
    version="1.0.0",
)

# ─────────────────────────────
# 🗃️ Datenbanktabellen beim Start sicherstellen
# ─────────────────────────────
init_db()   # ruft Base.metadata.create_all(bind=engine) intern auf

# ─────────────────────────────
# 🌐 Health Check / Startseite
# ─────────────────────────────
@app.get("/")
def redirect_to_login():
    return RedirectResponse(url="/auth/login")

# ─────────────────────────────
# 🖼 Statische Dateien (CSS, QR-Codes, PDFs)
# ─────────────────────────────
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# ─────────────────────────────
# 🔌 Router registrieren (Reihenfolge wichtig!)
# ─────────────────────────────
# ─────────────────────────────
# 1️⃣ Authentifizierung zuerst (Login, Token, Cookies)
# ─────────────────────────────
app.include_router(auth.router)              # Login / Auth MUSS ganz oben sein

# ─────────────────────────────
# 2️⃣ Dashboard & Admin-Bereich
# ─────────────────────────────
app.include_router(dashboard.router)         # Dashboard (geschützt)
app.include_router(admin.router)             # Adminbereich (geschützt, Rollenprüfung)
app.include_router(dashboard_users.router)   # Benutzerübersicht im Dashboard

# ─────────────────────────────
# 3️⃣ Kernmodule (interne Funktionen)
# ─────────────────────────────
app.include_router(users.router)             # Benutzerverwaltung
app.include_router(customers.router)         # Kundenverwaltung
app.include_router(products.router)         # Produkte
app.include_router(invoices.router)          # Rechnungen
app.include_router(reminders.router)         # Mahnungen 📨
app.include_router(payments.router)         # 💳 Zahlungen
app.include_router(orders.router)            # Bestellungen
app.include_router(leads.router)            # Leads
app.include_router(history.router)          # Verlauf / Historie
app.include_router(calendar.router)         # Kalender
app.include_router(ai_assistant.router)

# ─────────────────────────────
# 4️⃣ Kommunikation & Kanäle
# ─────────────────────────────
app.include_router(chat.router)
app.include_router(inbox.router)
app.include_router(channels_whatsapp.router)
app.include_router(calls_router)

# ─────────────────────────────
# 5️⃣ Berichte & Analyse
# ─────────────────────────────
app.include_router(reports.router)
app.include_router(campaigns.router)
app.include_router(segments.router)
app.include_router(audit.router)

# ─────────────────────────────
# 6️⃣ Einstellungen & Formulare
# ─────────────────────────────
app.include_router(settings.router)
app.include_router(forms.router)
app.include_router(integrations.router)
app.include_router(ai_settings.router)
# ─────────────────────────────
# 7️⃣ Öffentliche Seiten (ohne Login)
# ─────────────────────────────
app.include_router(public.router)           # Öffentliche Bestellseite
app.include_router(public_payment.router)
app.include_router(privacy.router)


# ─────────────────────────────
# ⚡ Session Middleware
# ─────────────────────────────
app.add_middleware(SessionMiddleware, secret_key="SUPERGEHEIM123")

# ─────────────────────────────
# 📴 Logout Redirect
# ─────────────────────────────
@app.get("/logout")
def logout_redirect():
    return RedirectResponse(url="/auth/logout", status_code=307)


# ─────────────────────────────
# 🔐 Zugriffsschutz: Weiterleitung auf Login-Seite
# ─────────────────────────────
from fastapi import Request

PUBLIC_PATHS = [
    "/",                      # Root
    "/auth/login",            # Login
    "/auth/token",
    "/auth/forgot-password",  # Passwort vergessen
    "/auth/reset-password",   # Passwort zurücksetzen
    "/static",                # CSS / Bilder
    "/favicon.ico"
]

@app.middleware("http")
async def auth_redirect_middleware(request: Request, call_next):
    path = request.url.path

    # 🔓 Öffentliche Routen zulassen
    if any(path.startswith(p) for p in PUBLIC_PATHS):
        return await call_next(request)

    # 🔐 Zugriff nur mit Cookie "access_token"
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/auth/login")

    # ✅ Wenn Token vorhanden → Anfrage weiterleiten
    response = await call_next(request)
    return response