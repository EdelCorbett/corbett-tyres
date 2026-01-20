import os
from uuid import uuid4
from datetime import date

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.invoices.models import Invoice, InvoiceAttachment
from app.invoices.schemas import InvoiceCreate

router = APIRouter(prefix="/invoices", tags=["invoices"])

UPLOAD_DIR = "uploads/invoices"


# -------------------------
# Database dependency
# -------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------------
# Create invoice
# -------------------------
@router.post("/")
def create_invoice(
    invoice: InvoiceCreate,
    db: Session = Depends(get_db),
):
    new_invoice = Invoice(
        customer_id=invoice.customer_id,
        invoice_date=invoice.invoice_date or date.today(),
        description=invoice.description,
        total_amount=invoice.total_amount,
        is_account=invoice.is_account,
        is_paid=False,
    )

    db.add(new_invoice)
    db.commit()
    db.refresh(new_invoice)

    return new_invoice


# -------------------------
# List invoices
# -------------------------
@router.get("/")
def list_invoices(db: Session = Depends(get_db)):
    return db.query(Invoice).order_by(Invoice.invoice_date.desc()).all()


@router.get("/customer/{customer_id}")
def list_customer_invoices(
    customer_id: int,
    db: Session = Depends(get_db),
):
    return (
        db.query(Invoice)
        .filter(Invoice.customer_id == customer_id)
        .order_by(Invoice.invoice_date.desc())
        .all()
    )


# -------------------------
# Upload invoice attachment
# -------------------------
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

