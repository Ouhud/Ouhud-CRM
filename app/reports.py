# app/reports.py
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import extract, func
from app.database import get_db
from app.models import Invoice

router = APIRouter(prefix="/dashboard/reports", tags=["Reports"])

templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
def reports_dashboard(request: Request, db: Session = Depends(get_db)):
    """
    📈 Berichte: Monatsumsatz aus Rechnungen aggregieren
    """
    # Umsatz gruppiert nach Monat im aktuellen Jahr
    results = (
        db.query(
            extract('month', Invoice.date).label('month'),
            func.sum(Invoice.total_amount).label('revenue')
        )
        .filter(extract('year', Invoice.date) == func.year(func.curdate()))
        .group_by('month')
        .order_by('month')
        .all()
    )

    months = [int(r.month) for r in results]
    revenues = [float(r.revenue) for r in results]

    return templates.TemplateResponse(
        "admin/reports.html",
        {
            "request": request,
            "months": months,
            "revenues": revenues
        }
    )