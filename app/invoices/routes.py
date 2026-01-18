import os
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from uuid import uuid4

from app.core.database import SessionLocal
from app.invoices.models import Invoice, InvoiceAttachment

router = APIRouter(prefix="/invoices", tags=["invoices"])

UPLOAD_DIR = "uploads/invoices"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/{invoice_id}/attachments")
def upload_invoice_attachment(
    invoice_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    file_ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())

    attachment = InvoiceAttachment(
        invoice_id=invoice_id,
        file_path=file_path,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    return {
        "message": "File uploaded successfully",
        "attachment_id": attachment.id,
        "file_path": attachment.file_path,
    }
