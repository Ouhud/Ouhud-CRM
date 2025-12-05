from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates

from app.database import get_db
from app.auth import get_current_user
from app.models import AutomationDesigner, User

router = APIRouter(prefix="/dashboard/automation", tags=["Automation Designer"])

templates = Jinja2Templates(directory="templates")


# ----------------------------------------------------------
# 1) Designer-Hauptseite
# ----------------------------------------------------------
@router.get("/designer")
def designer_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)   # ✅ Typ hinzugefügt
):
    workflows = db.query(AutomationDesigner).all()

    return templates.TemplateResponse(
        "dashboard/designer.html",
        {
            "request": request,
            "user": user,             # template expects "user"
            "workflows": workflows
        }
    )


# ----------------------------------------------------------
# 2) Neu speichern
# ----------------------------------------------------------
@router.post("/designer/save")
async def designer_save(
    name: str = Form(...),
    description: str = Form(""),
    json_data: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    workflow = AutomationDesigner(
        name=name,
        description=description,
        config_json=json_data
    )

    db.add(workflow)
    db.commit()

    return RedirectResponse("/dashboard/automation/designer", status_code=303)


# ----------------------------------------------------------
# 3) Workflow laden
# ----------------------------------------------------------
@router.get("/designer/{workflow_id}")
def designer_edit_page(
    workflow_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    wf = db.query(AutomationDesigner).filter_by(id=workflow_id).first()

    if not wf:
        raise HTTPException(status_code=404, detail="Workflow nicht gefunden")

    return templates.TemplateResponse(
        "dashboard/designer.html",
        {
            "request": request,
            "user": user,
            "workflow": wf
        }
    )


# ----------------------------------------------------------
# 4) Update speichern
# ----------------------------------------------------------
@router.post("/designer/{workflow_id}/save")
async def designer_update(
    workflow_id: int,
    name: str = Form(...),
    description: str = Form(""),
    json_data: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):

    wf = db.query(AutomationDesigner).filter_by(id=workflow_id).first()

    if not wf:
        raise HTTPException(status_code=404, detail="Workflow nicht gefunden")

    wf.name = name
    wf.description = description
    wf.config_json = json_data

    db.commit()

    return RedirectResponse("/dashboard/automation/designer", status_code=303)