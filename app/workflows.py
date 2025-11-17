from fastapi import APIRouter, Request, Depends, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.models_workflows import Workflow, WorkflowTrigger, WorkflowAction
from app.auth import require_admin

router = APIRouter(prefix="/dashboard/workflows", tags=["Workflows"])
templates = Jinja2Templates(directory="templates")


# ------------------------------------------------------------
# 1) Übersicht
# ------------------------------------------------------------
@router.get("/")
def list_workflows(request: Request, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    workflows = db.query(Workflow).all()
    return templates.TemplateResponse(
        "dashboard/workflows/index.html",
        {"request": request, "workflows": workflows, "user": user}
    )


# ------------------------------------------------------------
# 2) Neuer Workflow
# ------------------------------------------------------------
@router.get("/new")
def new_workflow(request: Request):
    return templates.TemplateResponse("dashboard/workflows/new.html", {"request": request})


@router.post("/new")
def create_workflow(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db)
):
    wf = Workflow(name=name, description=description)
    db.add(wf)
    db.commit()
    return RedirectResponse(f"/dashboard/workflows/{wf.id}/edit", status_code=303)


# ------------------------------------------------------------
# 3) Workflow bearbeiten (Main Page)
# ------------------------------------------------------------
@router.get("/{workflow_id}/edit")
def edit_workflow(workflow_id: int, request: Request, db: Session = Depends(get_db)):
    wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()

    triggers = db.query(WorkflowTrigger).filter_by(workflow_id=workflow_id).all()
    actions = db.query(WorkflowAction).filter_by(workflow_id=workflow_id).order_by(WorkflowAction.order_index).all()

    return templates.TemplateResponse(
        "dashboard/workflows/edit.html",
        {"request": request, "workflow": wf, "triggers": triggers, "actions": actions}
    )


# ------------------------------------------------------------
# 4) TRIGGER SPEICHERN
# ------------------------------------------------------------
@router.post("/{workflow_id}/edit/trigger/save")
def save_trigger(
    workflow_id: int,
    trigger_type: str = Form(...),
    config_json: str = Form(""),
    db: Session = Depends(get_db)
):

    # bestehenden Trigger löschen
    db.query(WorkflowTrigger).filter_by(workflow_id=workflow_id).delete()

    # neuen Trigger einfügen
    trig = WorkflowTrigger(
        workflow_id=workflow_id,
        trigger_type=trigger_type,
        config_json=config_json
    )
    db.add(trig)
    db.commit()

    return RedirectResponse(
        f"/dashboard/workflows/{workflow_id}/edit",
        status_code=303
    )


# ------------------------------------------------------------
# 5) ACTION HINZUFÜGEN
# ------------------------------------------------------------
@router.post("/{workflow_id}/edit/actions/add")
async def workflow_action_add(
    workflow_id: int,
    action_type: str = Form(...),
    config_json: str = Form(""),
    db: Session = Depends(get_db)
):
    last_action = (
        db.query(WorkflowAction)
        .filter(WorkflowAction.workflow_id == workflow_id)
        .order_by(WorkflowAction.order_index.desc())
        .first()
    )

    next_index = (last_action.order_index + 1) if last_action else 1

    new_action = WorkflowAction(
        workflow_id=workflow_id,
        action_type=action_type,
        config_json=config_json,
        order_index=next_index
    )

    db.add(new_action)
    db.commit()

    return RedirectResponse(
        url=f"/dashboard/workflows/{workflow_id}/edit",
        status_code=303
    )


# ------------------------------------------------------------
# 6) ACTION LÖSCHEN
# ------------------------------------------------------------
@router.post("/{workflow_id}/edit/actions/{action_id}/delete")
def delete_action(workflow_id: int, action_id: int, db: Session = Depends(get_db)):
    db.query(WorkflowAction).filter_by(id=action_id).delete()
    db.commit()

    return RedirectResponse(
        f"/dashboard/workflows/{workflow_id}/edit",
        status_code=303
    )


# ------------------------------------------------------------
# 7) ACTION BEARBEITEN / SPEICHERN
# ------------------------------------------------------------
@router.post("/{workflow_id}/edit/actions/{action_id}/save")
async def save_edit_action(
    workflow_id: int,
    action_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    form = await request.form()

    # Pylance-freundliche Typen:
    action_type: str = str(form.get("action_type") or "")
    config_json: str = str(form.get("config_json") or "")

    action = db.query(WorkflowAction).filter_by(id=action_id).first()

    if action is None:
        # Falls eine ungültige ID kam → zurück zur Seite
        return RedirectResponse(
            f"/dashboard/workflows/{workflow_id}/edit",
            status_code=303
        )

    action.action_type = action_type
    action.config_json = config_json

    db.commit()

    return RedirectResponse(
        f"/dashboard/workflows/{workflow_id}/edit",
        status_code=303
    )