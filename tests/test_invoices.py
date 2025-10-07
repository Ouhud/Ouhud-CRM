# tests/test_invoices.py
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_invoice_page_requires_login():
    r = client.get("/dashboard/invoices")
    assert r.status_code in (302, 307, 401)