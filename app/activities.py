# app/activities.py

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database import get_db
from app.models import Activity, User
from app.auth import get_current_user
from app.permissions import require_role
from app.utils.logging_utils import log_action
from app.utils.template_utils import render_template   # 🔥 GLOBAL FIX

router = APIRouter(
    prefix="/dashboard/activities",
    tags=["Activities"]
)


# --------------------------------------------------------------
# 1) LISTE ALLER AKTIVITÄTEN
# --------------------------------------------------------------
@router.get("/")
def list_activities(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # 🔥 Optional: Rechte prüfen
    require_role(current_user, ["admin", "mitarbeiter"])

    activities = (
        db.query(Activity)
        .order_by(Activity.created_at.desc())
        .all()
    )

    return render_template(
        request,
        "activities.html",
        {
            "activities": activities,
            "mode": "list"
        }
    )


# --------------------------------------------------------------
# 2) AKTIVITÄT ERSTELLEN (POST)
# --------------------------------------------------------------
@router.post("/create")
def create_activity(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    require_role(current_user, ["admin", "mitarbeiter"])

    activity = Activity(
        title=title,
        description=description,
        created_at=datetime.now(timezone.utc),
        user_id=current_user.id  # 🔥 Wer hat's erstellt?
    )

    db.add(activity)
    db.commit()
    db.refresh(activity)

    log_action(db, current_user.id, f"Aktivität erstellt: {title}")

    return RedirectResponse(
        "/dashboard/activities",
        status_code=303
    )


# --------------------------------------------------------------
# 3) DETAILSEITE EINER AKTIVITÄT
# --------------------------------------------------------------
@router.get("/{activity_id}")
def view_activity(
    activity_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    require_role(current_user, ["admin", "mitarbeiter"])

    activity = db.query(Activity).filter(Activity.id == activity_id).first()

    if not activity:
        raise HTTPException(404, "Aktivität nicht gefunden")

    return render_template(
        request,
        "activities.html",
        {
            "activity": activity,
            "mode": "detail"
        }
    )