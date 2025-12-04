#!/usr/bin/env python3
"""
CRM Reset + Demo-Daten Script
Führt das SQL-Script aus, um die DB zu resetten und Demo-Daten einzufügen.
"""

from app.database import engine
from sqlalchemy import text

# SQL Script als String
SQL_SCRIPT = """
SET FOREIGN_KEY_CHECKS = 0;

-- ==========================
-- 🔥 Tabellen leeren
-- ==========================
TRUNCATE TABLE activity_logs;
TRUNCATE TABLE password_reset_tokens;

TRUNCATE TABLE workflow_actions;
TRUNCATE TABLE workflow_triggers;
TRUNCATE TABLE workflows;

TRUNCATE TABLE invoice_items;
TRUNCATE TABLE invoices;

TRUNCATE TABLE products;
TRUNCATE TABLE customers;

TRUNCATE TABLE users;
TRUNCATE TABLE roles;
TRUNCATE TABLE role_permissions;

TRUNCATE TABLE companies;

SET FOREIGN_KEY_CHECKS = 1;

-- ==========================
-- 🏢 Demo Firma erstellen
-- ==========================
INSERT INTO companies (id, name, subdomain, custom_domain, owner_email, plan, status, created_at)
VALUES (
    1,
    'Ouhud Demo GmbH',
    'demo',
    NULL,
    'admin@demo.com',
    'pro',
    'active',
    NOW()
);

-- ==========================
-- 🔐 Demo Admin Rolle
-- ==========================
INSERT INTO roles (id, name, company_id)
VALUES (1, 'admin', 1);

-- ==========================
-- 👤 Demo Admin User anlegen
-- Passwort ist: demo1234
-- ==========================
INSERT INTO users (
    id,
    username,
    email,
    hashed_password,
    company_id,
    role_id,
    is_active,
    created_at
) VALUES (
    1,
    'demo_admin',
    'admin@demo.com',
    '$2b$12$W8yT72hF.xxxxxxxxxxxxxxxxDmFq',  -- WICHTIG: WIRD UNTEN ERSETZT!
    1,
    1,
    1,
    NOW()
);

-- ==========================
-- 🛍 Beispiel-Produkte
-- ==========================
INSERT INTO products (name, description, price, active)
VALUES
('Premium Support', '24/7 Support für alle Geräte', 49.99, 1),
('Cloud Speicher', 'Zusätzliche 200GB', 5.99, 1),
('Team Lizenz', 'Bis zu 5 Mitarbeiter', 19.99, 1);

-- ==========================
-- 🧑‍🤝‍🧑 Beispiel-Kunden
-- ==========================
INSERT INTO customers (company_id, name, email)
VALUES
(1, 'Testkunde GmbH', 'kontakt@testkunde.com'),
(1, 'Muster AG', 'info@muster.com');

-- ==========================
-- 💡 Automatisch Passwort setzen
-- (Passwort = demo1234)
-- ==========================
UPDATE users
SET hashed_password = '$2b$12$gImKCxP3gY43HqFQ37zDxOqP.a9E0V8Nw1J9tY8/CMfOQvmXwCLjG'
WHERE id = 1;

-- Hash wurde erzeugt mit:
-- python3 -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('demo1234'))"

-- ==========================
-- ✔ Abschlussmeldung
-- ==========================
SELECT "CRM Reset + Demo-Daten erfolgreich installiert." AS status;
"""

def main():
    print("🔄 Starte CRM Reset + Demo-Daten Installation...")

    try:
        with engine.connect() as conn:
            # SQL Script in einzelne Statements splitten
            statements = [stmt.strip() for stmt in SQL_SCRIPT.split(';') if stmt.strip() and not stmt.strip().startswith('--')]

            for stmt in statements:
                if stmt:
                    print(f"Ausführen: {stmt[:50]}...")
                    conn.execute(text(stmt))
            conn.commit()
            print("✅ CRM Reset + Demo-Daten erfolgreich installiert!")

    except Exception as e:
        print(f"❌ Fehler beim Ausführen des Scripts: {e}")
        return False

    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("🎉 Fertig!")
    else:
        print("💥 Abbruch wegen Fehler.")
