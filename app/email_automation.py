# app/routes/email_automation.py

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.database import get_automations_from_db, save_automation_to_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# ------------------------------------------------------------
#  Automatisierungs-Seite anzeigen
# ------------------------------------------------------------
@router.get("/dashboard/email/automation")
def email_automation(request: Request):
    automations = get_automations_from_db()
    return templates.TemplateResponse(
        "email/automation.html",
        {
            "request": request,
            "active_tab": "automation",
            "automations": automations
        }
    )


# ------------------------------------------------------------
#  Neue Automatisierungsregel speichern
# ------------------------------------------------------------
@router.post("/dashboard/email/automation/new")
def create_rule(
    request: Request,
    title: str = Form(...),
    trigger: str = Form(...),
    message: str = Form(...)
):
    save_automation_to_db(title, trigger, message)

    return RedirectResponse(
        "/dashboard/email/automation",
        status_code=303
    )