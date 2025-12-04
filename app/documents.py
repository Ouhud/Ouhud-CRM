from __future__ import annotations
from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Depends,
    Request,
    HTTPException,
    Query,
    Form
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional
from pathlib import Path
import shutil
import os

from app.database import get_db
from app.models import Document, User, UserRole, Customer, LeadDB
from app.auth import get_current_user   # 🔥 Einheitlich wie anderes CRM

# -----------------------------------------------------
# ROUTER
# -----------------------------------------------------
router = APIRouter(
    prefix="/dashboard/documents",
    tags=["Documents"]
)

# -----------------------------------------------------
# KONSTANTEN
# -----------------------------------------------------
UPLOAD_FOLDER = Path("app/static/documents")
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".docx"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------
# HELPER
# -----------------------------------------------------
def is_allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def get_file_size(file: UploadFile) -> int:
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    return size


# -----------------------------------------------------
# 1) Dokumentseite (Übersicht)
# -----------------------------------------------------
@router.get("/")
def documents_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100)
):
    query = db.query(Document).filter(Document.uploaded_by == current_user.id)

    if category:
        query = query.filter(Document.category == category)

    if search:
        query = query.filter(Document.filename.contains(search))

    total = query.count()
    docs = (
        query.order_by(Document.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    customers = db.query(Customer).all()
    leads = db.query(LeadDB).all()

    return request.app.state.templates.TemplateResponse(
        "dashboard/documents.html",
        {
            "request": request,
            "documents": docs,
            "customers": customers,
            "leads": leads,
            "category": category,
            "search": search,
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page,
            "current_user": current_user,
        },
    )


# -----------------------------------------------------
# 2) Upload Dokument
# -----------------------------------------------------
@router.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    category: Optional[str] = Form(None),
    customer_id: Optional[int] = Form(None),
    lead_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename or not is_allowed_file(file.filename):
        raise HTTPException(status_code=400, detail="Ungültiger Dateityp.")

    if get_file_size(file) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Datei zu groß (max. 10MB).")

    filename = file.filename
    filepath = UPLOAD_FOLDER / filename

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    doc = Document(
        filename=filename,
        path=str(filepath),
        category=category,
        uploaded_by=current_user.id,
        file_size=get_file_size(file),
        file_type=Path(filename).suffix.lower(),
        customer_id=customer_id,
        lead_id=lead_id,
    )

    db.add(doc)
    db.commit()
    db.refresh(doc)

    return {
        "status": "ok",
        "filename": filename,
        "document_id": doc.id
    }


# -----------------------------------------------------
# 3) Download
# -----------------------------------------------------
@router.get("/download/{doc_id}")
def download_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.uploaded_by == current_user.id)
        .first()
    )

    if not doc:
        raise HTTPException(status_code=404, detail="Dokument nicht gefunden.")

    if not Path(doc.path).exists():
        raise HTTPException(status_code=404, detail="Datei fehlt auf dem Server.")

    return FileResponse(doc.path, filename=doc.filename)


# -----------------------------------------------------
# 4) Delete
# -----------------------------------------------------
@router.post("/delete/{doc_id}")
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.query(Document).filter(Document.id == doc_id).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Dokument existiert nicht.")

    if doc.uploaded_by != current_user.id and current_user.role.name != UserRole.admin:
        raise HTTPException(status_code=403, detail="Keine Berechtigung.")

    try:
        if os.path.exists(doc.path):
            os.remove(doc.path)
    except:
        pass

    db.delete(doc)
    db.commit()

    return {"status": "deleted", "id": doc_id}