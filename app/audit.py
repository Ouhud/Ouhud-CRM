# app/audit.py
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from datetime import datetime, timedelta

from fastapi.templating import Jinja2Templates

from app.database import SessionLocal
from app.auth import get_current_user, User
from app.models import AuditLog

# ------------------------------------------------------------
# Templates aktivieren
# ------------------------------------------------------------
templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/dashboard/audit", tags=["Audit"])


# ------------------------------------------------------------
# DB Session Factory
# ------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================
# AUDIT DASHBOARD
# ============================================================
@router.get("/", response_class=HTMLResponse)
async def audit_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = request.query_params.get("q", "")
    action_filter = request.query_params.get("action", "")
    range_filter = request.query_params.get("range", "")

    query = db.query(AuditLog).filter(AuditLog.company_id == user.company_id)

    # 🔍 Suche
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                AuditLog.user.ilike(like),
                AuditLog.action.ilike(like),
                AuditLog.details.ilike(like),
                AuditLog.ip_address.ilike(like),
            )
        )

    # 🎯 Aktion Filter
    if action_filter:
        query = query.filter(AuditLog.action == action_filter)

    # ⏰ Zeitraum
    now = datetime.utcnow()

    if range_filter == "today":
        start = now.replace(hour=0, minute=0, second=0)
        query = query.filter(AuditLog.timestamp >= start)

    elif range_filter == "7":
        start = now - timedelta(days=7)
        query = query.filter(AuditLog.timestamp >= start)

    elif range_filter == "30":
        start = now - timedelta(days=30)
        query = query.filter(AuditLog.timestamp >= start)

    # Daten abrufen
    logs = query.order_by(AuditLog.timestamp.desc()).limit(300).all()

    # ============================================================
    # KPI STATISTIKEN
    # ============================================================
    stats = {
        "logins": db.query(func.count())
                    .select_from(AuditLog)
                    .filter_by(company_id=user.company_id, action="login")
                    .scalar(),

        "changes": db.query(func.count())
                     .select_from(AuditLog)
                     .filter(
                         AuditLog.company_id == user.company_id,
                         AuditLog.action.in_(["create", "update", "delete"]),
                     )
                     .scalar(),

        "errors": db.query(func.count())
                    .select_from(AuditLog)
                    .filter_by(company_id=user.company_id, action="error")
                    .scalar(),
    }

    return templates.TemplateResponse(
        "audit.html",
        {
            "request": request,
            "user": user,
            "company": user.company,
            "logs": logs,
            "stats": stats,
            "q": q,
            "action_filter": action_filter,
            "range_filter": range_filter,
        }
    )


# ============================================================
# EINZELDETAIL → MODAL / POPUP
# ============================================================
@router.get("/details/{log_id}")
def audit_details(
    log_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    log = db.get(AuditLog, log_id)

    if not log or log.company_id != user.company_id:
        return JSONResponse({"error": "Nicht gefunden"}, 404)

    return JSONResponse({
        "id": log.id,
        "action": log.action,
        "user": log.user,
        "details": log.details,
        "ip": log.ip_address,
        "timestamp": log.timestamp.isoformat(),
    })


# ============================================================
# CSV EXPORT
# ============================================================
@router.get("/export")
def audit_export(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.company_id == user.company_id)
        .order_by(AuditLog.timestamp.desc())
        .all()
    )

    def generate():
        yield "timestamp,user,action,details,ip\n"
        for log in logs:
            details_clean = (log.details or "").replace(",", ";")
            yield f"{log.timestamp},{log.user},{log.action},{details_clean},{log.ip_address}\n"

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=audit_logs.csv"
        }
    )