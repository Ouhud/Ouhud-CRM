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
            "user": current_user,       # ← 🔥 WICHTIG! Template braucht „user“

        },
    )


# -----------------------------------------------------
# 2) Upload Dokument
# -----------------------------------------------------
from datetime import datetime
import uuid

@router.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    category: Optional[str] = Form(None),
    customer_id: Optional[str] = Form(None),
    lead_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # ---------------------------
    # Validate file type
    # ---------------------------
    if not file.filename or not is_allowed_file(file.filename):
        raise HTTPException(status_code=400, detail="Ungültiger Dateityp.")

    # Validate content type (security)
    allowed_mime = {
        "application/pdf",
        "image/jpeg",
        "image/png",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    if file.content_type not in allowed_mime:
        raise HTTPException(status_code=400, detail="Datei-Typ nicht erlaubt.")

    # Validate file size
    size = get_file_size(file)
    if size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Datei zu groß (max. 10MB).")

    # ---------------------------
    # Normalize customer/lead
    # ---------------------------
    def clean_int(value):
        return int(value) if value not in (None, "", "null", "undefined") else None

    customer_id = clean_int(customer_id)
    lead_id = clean_int(lead_id)

    # ---------------------------
    # Create dynamic folder structure
    # ---------------------------
    now = datetime.utcnow()

    user_folder = Path(
        f"app/static/documents/{current_user.company_id}/{current_user.id}/{now.year}/{now.month}"
    )
    user_folder.mkdir(parents=True, exist_ok=True)

    # ---------------------------
    # Unique filename
    # ---------------------------
    ext = Path(file.filename).suffix
    safe_name = Path(file.filename).stem.replace(" ", "_")

    unique_name = f"{safe_name}_{uuid.uuid4().hex[:12]}{ext}"
    full_path = user_folder / unique_name

    # ---------------------------
    # Save file
    # ---------------------------
    with open(full_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # ---------------------------
    # Create DB record
    # ---------------------------
    doc = Document(
        company_id=current_user.company_id,   # 🔥 WICHTIG!
        filename=file.filename,
        path=str(full_path),
        category=category,
        uploaded_by=current_user.id,
        file_size=size,
        file_type=ext,
        customer_id=customer_id,
        lead_id=lead_id,
    )

    db.add(doc)
    db.commit()
    db.refresh(doc)

    return {
    "ok": True,
    "message": "Dokument erfolgreich hochgeladen.",
    "document_id": doc.id,
    "filename": file.filename,
    "saved_as": unique_name,
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