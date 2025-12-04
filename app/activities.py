# app/activities.py

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database import get_db
from app.models import Activity   # HIER muss dein Activity-Modell vorhanden sein

router = APIRouter(
    prefix="/dashboard/activities",
    tags=["Activities"]
)

# Templates laden
templates = Jinja2Templates(directory="templates")


# ------------------------------------------------------------------
# 1. LISTE ALLER AKTIVITÄTEN (GET /dashboard/activities)
# ------------------------------------------------------------------
@router.get("/")
def list_activities(request: Request, db: Session = Depends(get_db)):

    activities = db.query(Activity).order_by(Activity.created_at.desc()).all()

    return templates.TemplateResponse(
        "activities.html",
        {
            "request": request,
            "activities": activities,
        }
    )


# ------------------------------------------------------------------
# 2. NEUE AKTIVITÄT ERSTELLEN (POST /dashboard/activities/create)
# ------------------------------------------------------------------
@router.post("/create")
def create_activity(
    request: Request,
    db: Session = Depends(get_db),
    title: str = Form(...),
    description: str = Form(""),
):

    activity = Activity(
        title=title,
        description=description,
        created_at=datetime.now(timezone.utc)   # Aware datetime
    )

    db.add(activity)
    db.commit()
    db.refresh(activity)

    return RedirectResponse(url="/dashboard/activities", status_code=303)


# ------------------------------------------------------------------
# 3. DETAILSEITE (OPTIONAL) – GET /dashboard/activities/{id}
# ------------------------------------------------------------------
@router.get("/{activity_id}")
def view_activity(activity_id: int, request: Request, db: Session = Depends(get_db)):

    activity = db.query(Activity).filter(Activity.id == activity_id).first()

    return templates.TemplateResponse(
        "activities.html",
        {
            "request": request,
            "activity": activity,
        }
    )