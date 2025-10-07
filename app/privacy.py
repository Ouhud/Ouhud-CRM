from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
import os

router = APIRouter()

# 📌 Richtiger Template-Pfad: eine Ebene über /app → /CRM/templates
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

@router.get("/dashboard/privacy")
async def privacy_page(request: Request):
    return templates.TemplateResponse(request, "privacy.html", {"request": request})