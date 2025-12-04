# main.py
import os
from app import audit
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from app.company import router as company_router
from app import offers
from app.email_providers import router as email_providers_router

from app.email_automation import router as automation_router
from app import activities

from typing import Callable, Awaitable
from app.tenants.tenant_middleware import TenantMiddleware
from app.subscription_routes import router as subscription_router


# Auth
from app.auth_utils import get_user_from_token

# DB
from app.database import init_db

# Router-Module
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
    ai_assistant,
    ai_settings,
    ai_leads,
)

from app.channels_calls import router as calls_router
from app.documents import router as documents_router
from app.workflows import router as workflows_router
from app.automation_designer import router as automation_designer_router


# ─────────────────────────────
# Templates
# ─────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

app = FastAPI(
    title="Ouhud CRM",
    description="Professionelles CRM-System",
    version="1.0.0",
)

app.state.templates = templates

# DB Tables
init_db()

app.add_middleware(TenantMiddleware)


# Static Files
app.mount("/static", StaticFiles(directory="app/static"), name="static")


# ─────────────────────────────
# LOGIN REDIRECT
# ─────────────────────────────
@app.get("/")
def homepage(request: Request):
    return templates.TemplateResponse("landing.html", {"request": request})

# ─────────────────────────────
# ROUTER REGISTRIEREN
# ─────────────────────────────
# Auth + Dashboard
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
app.include_router(company_router)

app.include_router(offers.router)

app.include_router(email_providers_router)

app.include_router(automation_router)

app.include_router(subscription_router)

# Kommunikation
app.include_router(chat.router)
app.include_router(inbox.router)
app.include_router(channels_whatsapp.router)
app.include_router(calls_router)

# KI
app.include_router(ai_assistant.router)
app.include_router(ai_leads.router)
app.include_router(ai_settings.router)

# Dokumente & Workflows
app.include_router(documents_router)
app.include_router(workflows_router)
app.include_router(automation_designer_router)

# Reports
app.include_router(reports.router)
app.include_router(campaigns.router)
app.include_router(segments.router)
app.include_router(audit.router)

# Settings
app.include_router(settings.router)
app.include_router(forms.router)
app.include_router(integrations.router)

# Public
app.include_router(public.router)
app.include_router(public_payment.router)
app.include_router(privacy.router)

app.include_router(activities.router)
# ─────────────────────────────
# SESSION MIDDLEWARE
# ─────────────────────────────
app.add_middleware(SessionMiddleware, secret_key="SUPERGEHEIM123")

# ─────────────────────────────
# LOGOUT ROUTE
# ─────────────────────────────
@app.get("/logout")
def logout_redirect():
    return RedirectResponse("/auth/logout", status_code=307)


# ─────────────────────────────
# AUTH-MIDDLEWARE (stabil)
# ─────────────────────────────
PUBLIC_PATHS = {
    "/", "/auth/login", "/auth/token",
    "/auth/forgot-password", "/auth/reset-password",
    "/static", "/favicon.ico",
}

STATIC_EXTENSIONS = (
    ".css", ".js", ".png", ".jpg", ".jpeg",
    ".svg", ".gif", ".ico", ".webp"
)

@app.middleware("http")
async def auth_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    
    path = request.url.path

    # 🌍 Öffentlich zugängliche Routen (kein Login nötig)
    PUBLIC_PATHS = [
        "/",                    # Landing Page
        "/pricing",             # Tarife
        "/register",            # Registrierung
        "/auth/login",
        "/auth/token",
        "/auth/forgot-password",
        "/auth/reset-password",
    ]

    # 🟦 Wenn die Route öffentlich ist → Weiter ohne Authentifizierung
    if (
        path in PUBLIC_PATHS
        or path.startswith("/static")
        or path.startswith("/public")
        or path.startswith("/auth")   # erlaubt alle /auth/* Routen
    ):
        return await call_next(request)

    # 🔐 Token prüfen
    token = request.cookies.get("access_token")

    if not token:
        return RedirectResponse("/auth/login", status_code=302)

    # 🧑 Benutzer anhand Token laden
    user = await get_user_from_token(token)

    if not user:
        # Token ungültig → löschen & zurück zum Login
        resp = RedirectResponse("/auth/login", status_code=302)
        resp.delete_cookie("access_token")
        return resp

    # ✔️ User speichern für Sidebar / Templates / Rollen
    request.state.user = user

    # Anfrage verarbeiten
    response = await call_next(request)

    # Falls jemand auf geschützten Bereich kommt ohne Berechtigung
    if response.status_code == 401:
        return RedirectResponse("/auth/login", status_code=302)

    return response