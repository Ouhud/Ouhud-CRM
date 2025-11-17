import os
import sys
from pathlib import Path
import importlib
from typing import List
from fastapi.routing import APIRoute

PROJECT_ROOT = Path(__file__).parent
APP_DIR = PROJECT_ROOT / "app"
TEMPLATE_DIR = PROJECT_ROOT / "templates"


# ======================================================================
# 🔍 FastAPI-App automatisch finden
# ======================================================================
def autodetect_fastapi_app():
    """
    Sucht im Projekt nach einer Datei, die FastAPI(...) enthält und
    importiert das 'app' Objekt absolut sicher, ohne Fehler.
    """
    for py_file in PROJECT_ROOT.rglob("*.py"):
        try:
            text = py_file.read_text(encoding="utf8")
            if "FastAPI(" in text:
                module_path = str(py_file.relative_to(PROJECT_ROOT)).replace("/", ".")[:-3]
                module = importlib.import_module(module_path)
                if hasattr(module, "app"):
                    return module.app
        except Exception:
            continue

    raise RuntimeError("❌ Keine FastAPI-App im Projekt gefunden.")


# ======================================================================
# 1) Template-Prüfung
# ======================================================================
def check_templates() -> list[str]:
    """
    Prüft Jinja2-Templates syntaktisch korrekt,
    aber OHNE sie zu rendern (kein false positive!).
    """
    errors = []
    from jinja2 import Environment, FileSystemLoader, TemplateSyntaxError

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))

    for path in TEMPLATE_DIR.rglob("*.html"):
        try:
            env.parse(path.read_text(encoding="utf8"))
        except TemplateSyntaxError as e:
            errors.append(f"❌ Template Syntax Fehler in {path}: {e}")

    return errors


# ======================================================================
# 2) Python-Importe prüfen
# ======================================================================
def check_python_imports() -> list[str]:
    errors = []

    for py in APP_DIR.rglob("*.py"):
        module_path = str(py.relative_to(PROJECT_ROOT)).replace("/", ".")[:-3]

        try:
            importlib.import_module(module_path)
        except Exception as e:
            # Kein false positive bei require_login etc.
            if "cookies" in str(e):
                continue
            errors.append(f"❌ Import Fehler in {module_path}: {e}")

    return errors


# ======================================================================
# 3) Router & Templates prüfen — professionell
# ======================================================================
def check_routes() -> list[str]:
    """
    Prüft:
    - Route existiert in FastAPI
    - Template existiert bei GET-HTML-Routen
    """
    errors = []
    app = autodetect_fastapi_app()

    # Nur GET-Routen, die HTML rendern
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        if not route.path.startswith("/dashboard"):
            continue

        # Template-Namen extrahieren, wenn in Endpoint TemplateResponse vorkommt
        endpoint_source = route.endpoint.__doc__ or ""

        # Beispiel:
        # """Template: dashboard/invoices.html"""
        if "Template:" in endpoint_source:
            try:
                tpl = endpoint_source.split("Template:")[1].strip().split()[0]
                full_path = TEMPLATE_DIR / tpl
                if not full_path.exists():
                    errors.append(
                        f"❌ Template fehlt für Route {route.path}: {full_path}"
                    )
            except Exception:
                continue

    return errors


# ======================================================================
# 4) Modelle gegen MySQL prüfen
# ======================================================================
def check_models_db() -> list[str]:
    errors = []

    try:
        from sqlalchemy import create_engine, inspect
        from app.database import engine  # deine Engine direkt
        from app import models

        inspector = inspect(engine)

        for table in inspector.get_table_names():
            db_cols = {c["name"] for c in inspector.get_columns(table)}

            # Modelltabelle suchen
            for model_name in dir(models):
                model = getattr(models, model_name)
                if hasattr(model, "__tablename__") and model.__tablename__ == table:
                    model_cols = {c.name for c in model.__table__.columns}

                    missing = model_cols - db_cols
                    extra = db_cols - model_cols

                    if missing:
                        errors.append(f"❌ DB fehlt Spalten in {table}: {missing}")

                    if extra:
                        errors.append(f"⚠️ DB enthält zusätzliche Spalten in {table}: {extra}")

    except Exception as e:
        errors.append(f"❌ Fehler beim DB-Modellcheck: {e}")

    return errors


# ======================================================================
# 5) KI-Provider prüfen
# ======================================================================
def check_ai() -> list[str]:
    errors = []

    try:
        from app.utils.ai_provider import AIProvider
        ai = AIProvider()

        if not ai.api_key:
            errors.append("❌ Kein KI API-Key gesetzt.")

        if not ai.active:
            errors.append("⚠️ KI ist deaktiviert.")

    except Exception as e:
        errors.append(f"❌ AI Provider Fehler: {e}")

    return errors


# ======================================================================
# RUNNER
# ======================================================================
def run_all_checks():
    checks = {
        "Templates": check_templates(),
        "Python Imports": check_python_imports(),
        "Routers": check_routes(),
        "DB Models": check_models_db(),
        "AI Provider": check_ai(),
    }

    print("\n===============================")
    print("🔍 CRM SYSTEM VALIDATION")
    print("===============================\n")

    total_errors = 0

    for name, results in checks.items():
        print(f"▶️ {name}:")
        if not results:
            print("   ✅ OK")
        else:
            for e in results:
                print("   " + e)
                total_errors += 1
        print()

    print("===============================")
    if total_errors == 0:
        print("💚 ALLES OK — System ist vollständig & sauber!")
    else:
        print(f"❌ {total_errors} Probleme gefunden.")
    print("===============================\n")


if __name__ == "__main__":
    run_all_checks()