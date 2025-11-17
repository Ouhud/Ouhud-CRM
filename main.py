# main.py
import os
from typing import Callable 


from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import RedirectResponse


# 🔌 Module
from app import audit
from app import ai_assistant
from app import ai_settings

# 📌 Importiere deine Routen sauber
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
from app import ai_leads

# 📞 Calls separat
from app.channels_calls import router as calls_router

# 🛢️ DB initialisieren
from app.database import init_db
from app.workflows import router as workflows_router

# ─────────────────────────────
# 🧭 Templates global
# ─────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


# ─────────────────────────────
# 🚀 FastAPI App erstellen
# ─────────────────────────────
app = FastAPI(
    title="Ouhud CRM",
    description="Professionelles CRM-System für Rechnungs- und Kundenverwaltung",
    version="1.0.0",
)

# 🗃️ Tabellen erzeugen
init_db()


# ─────────────────────────────
# 🔄 Root → Login
# ─────────────────────────────
@app.get("/")
def redirect_to_login() -> RedirectResponse:
    return RedirectResponse(url="/auth/login")


# ─────────────────────────────
# 🖼 Static
# ─────────────────────────────
app.mount("/static", StaticFiles(directory="app/static"), name="static")


# ─────────────────────────────
# 🔌 Router registrieren
# ─────────────────────────────
app.include_router(auth.router)

app.include_router(dashboard.router)
app.include_router(admin.router)
app.include_router(dashboard_users.router)

# Kernmodule
app.include_router(users.router)
app.include_router(customers.router)
app.include_router(products.router)
app.include_router(invoices.router)
app.include_router(reminders.router)
app.include_router(payments.router)
app.include_router(orders.router)
app.include_router(leads.router)
app.include_router(history.router)
app.include_router(calendar.router)
app.include_router(ai_assistant.router)

# Kommunikation
app.include_router(chat.router)
app.include_router(inbox.router)
app.include_router(channels_whatsapp.router)
app.include_router(calls_router)

# Reports
app.include_router(reports.router)
app.include_router(campaigns.router)
app.include_router(segments.router)
app.include_router(audit.router)

# Einstellungen
app.include_router(settings.router)
app.include_router(forms.router)
app.include_router(integrations.router)
app.include_router(ai_settings.router)

# Öffentlich
app.include_router(public.router)
app.include_router(public_payment.router)
app.include_router(privacy.router)
app.include_router(ai_leads.router)

# ─────────────────────────────
# ⚡ Session Middleware
# ─────────────────────────────
app.add_middleware(SessionMiddleware, secret_key="SUPERGEHEIM123")



app.include_router(workflows_router)
# ─────────────────────────────
# 🔌 Logout
# ─────────────────────────────
@app.get("/logout")
def logout_redirect() -> RedirectResponse:
    return RedirectResponse(url="/auth/logout", status_code=307)

# ---------------------------------------------------
# 🔐 Auth-Middleware (stabil, kein falsches Logout)
# ---------------------------------------------------

PUBLIC_PATHS = [
    "/",
    "/auth/login",
    "/auth/token",
    "/auth/forgot-password",
    "/auth/reset-password",
    "/static",
    "/favicon.ico",
]

STATIC_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".css", ".js", ".ico")


@app.middleware("http")
async def auth_redirect_middleware(
    request: Request,
    call_next: Callable[[Request], Response]
) -> Response:

    path = request.url.path

    if any(path.startswith(p) for p in PUBLIC_PATHS) or path.endswith(STATIC_EXTENSIONS):
        return await call_next(request)

    token = request.cookies.get("access_token")

    if not token:
        return RedirectResponse(url="/auth/login")

    result = await call_next(request)
    return result