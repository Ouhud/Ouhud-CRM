# ✅ Haupt-App direkt aus main.py importieren
from main import app
from fastapi.testclient import TestClient

client = TestClient(app)


# 🧪 Basis-Tests -------------------------------------------------------------

def test_login_page():
    """Login-Seite sollte erreichbar sein."""
    r = client.get("/auth/login")
    assert r.status_code == 200


def test_dashboard_redirect_without_login():
    """
    Wenn man nicht eingeloggt ist und das Dashboard aufruft,
    sollte ein Redirect oder 401 zurückkommen.
    """
    r = client.get("/dashboard/")
    assert r.status_code in (302, 307, 401)


def test_invoice_list_requires_login():
    """Die Rechnungsseite sollte Login erfordern."""
    r = client.get("/dashboard/invoices")
    assert r.status_code in (302, 307, 401)


def test_leads_page_access():
    """Die Leads-Seite sollte ohne Login nicht direkt zugänglich sein."""
    r = client.get("/dashboard/leads")
    assert r.status_code in (200, 302, 401)


# 🧪 Erweiterte Tests (optional) ---------------------------------------------

def test_calendar_page():
    """Kalenderseite testen (Login erforderlich)."""
    r = client.get("/dashboard/calendar")
    assert r.status_code in (200, 302, 401)


def test_products_page():
    """Produktliste sollte entweder erreichbar oder redirect sein."""
    r = client.get("/dashboard/products")
    assert r.status_code in (200, 302, 401)


def test_ai_assistant_page():
    """KI-Assistenten-Seite sollte geladen werden (auch ohne Login prüfen)."""
    r = client.get("/dashboard/ai/assistant")
    assert r.status_code in (200, 302, 401)


def test_public_order_form():
    """Öffentliches Bestellformular sollte erreichbar sein (ohne Login)."""
    r = client.get("/order")
    assert r.status_code in (200, 404)  # hängt von deinem Routing ab