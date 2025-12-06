import os
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.auth import get_current_user

from app.models import Team, User

router = APIRouter(prefix="/dashboard/teams", tags=["Teams"])

# 📁 Template-Pfad
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


# ---------------------------------------------------------
# 📋 TEAM LISTE
# ---------------------------------------------------------
@router.get("/", response_class=HTMLResponse)
def list_teams(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    company = request.state.company

    teams = db.query(Team).filter(Team.company_id == company.id).all()

    return templates.TemplateResponse(
        "dashboard/teams.html",
        {"request": request, "user": user, "teams": teams}
    )


# ---------------------------------------------------------
# ➕ FORMULAR: Team erstellen
# ---------------------------------------------------------
@router.get("/create", response_class=HTMLResponse)
def create_team_form(request: Request, db: Session = Depends(get_db)):
    all_users = db.query(User).filter(User.company_id == request.state.company.id).all()

    return templates.TemplateResponse(
        "dashboard/team_form.html",
        {
            "request": request,
            "user": request.state.user,
            "all_users": all_users,
            "company": request.state.company
        }
    )


# ---------------------------------------------------------
# 💾 SPEICHERN: Team erstellen
# ---------------------------------------------------------
@router.post("/create")
def create_team(
    request: Request,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    members: Optional[List[int]] = Form(None),
    db: Session = Depends(get_db)
):
    team = Team(
        name=name,
        description=description,
        company_id=request.state.company.id
    )

    # Mitglieder hinzufügen
    if members:
        team_members = db.query(User).filter(
            User.id.in_(members),
            User.company_id == request.state.company.id
        ).all()

        team.members = team_members

    db.add(team)
    db.commit()

    return RedirectResponse("/dashboard/teams", status_code=303)


# ---------------------------------------------------------
# ✏️ FORMULAR: Team bearbeiten
# ---------------------------------------------------------
@router.get("/edit/{team_id}", response_class=HTMLResponse)
def edit_team_form(team_id: int, request: Request, db: Session = Depends(get_db)):
    team = db.query(Team).filter(
        Team.id == team_id,
        Team.company_id == request.state.company.id
    ).first()

    if not team:
        return RedirectResponse("/dashboard/teams", status_code=303)

    all_users = db.query(User).filter(User.company_id == request.state.company.id).all()

    return templates.TemplateResponse(
        "dashboard/team_form.html",
        {
            "request": request,
            "user": request.state.user,
            "team": team,
            "all_users": all_users,
            "company": request.state.company
        }
    )


# ---------------------------------------------------------
# 💾 SPEICHERN: Team aktualisieren
# ---------------------------------------------------------
@router.post("/edit/{team_id}")
def edit_team(
    team_id: int,
    request: Request,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    members: Optional[List[int]] = Form(None),
    db: Session = Depends(get_db)
):
    team = db.query(Team).filter(
        Team.id == team_id,
        Team.company_id == request.state.company.id
    ).first()

    if not team:
        return RedirectResponse("/dashboard/teams", status_code=303)

    team.name = name
    team.description = description

    # Team-Mitglieder aktualisieren
    if members is not None:
        team_members = db.query(User).filter(
            User.id.in_(members),
            User.company_id == request.state.company.id
        ).all()
        team.members = team_members

    db.commit()

    return RedirectResponse("/dashboard/teams", status_code=303)


# ---------------------------------------------------------
# 🗑️ LÖSCHEN: Team
# ---------------------------------------------------------
@router.get("/delete/{team_id}")
def delete_team(team_id: int, request: Request, db: Session = Depends(get_db)):
    team = db.query(Team).filter(
        Team.id == team_id,
        Team.company_id == request.state.company.id
    ).first()

    if team:
        db.delete(team)
        db.commit()

    return RedirectResponse("/dashboard/teams", status_code=303)


# ---------------------------------------------------------
# 👁️ DETAILS: Team anzeigen
# ---------------------------------------------------------
@router.get("/{team_id}", response_class=HTMLResponse)
def team_detail(team_id: int, request: Request, db: Session = Depends(get_db)):
    team = db.query(Team).filter(
        Team.id == team_id,
        Team.company_id == request.state.company.id
    ).first()

    if not team:
        return RedirectResponse("/dashboard/teams", status_code=303)

    return templates.TemplateResponse(
        "dashboard/team_detail.html",
        {
            "request": request,
            "user": request.state.user,
            "team": team,
            "company": request.state.company
        }
    )
