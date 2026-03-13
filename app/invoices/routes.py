import os
from sqlalchemy import func
from datetime import date, datetime 
from uuid import uuid4

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
    # Current year
    year = (invoice.invoice_date or date.today()).year

    # Count invoices created this year
    count = db.query(func.count(Invoice.id)).filter(
        func.extract("year", Invoice.invoice_date) == year
    ).scalar()

    next_number = count + 1

    # Generate invoice number
    invoice_number = f"INV-{year}-{next_number:04d}"

    new_invoice = Invoice(
        invoice_number=invoice_number,
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

@router.patch("/{invoice_id}/pay")
def mark_invoice_paid(
    invoice_id: int,
    db: Session = Depends(get_db),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if invoice.is_paid:
        return {"message": "Invoice already marked as paid"}

    invoice.is_paid = True
    db.commit()

    return {
        "message": "Invoice marked as paid",
        "invoice_id": invoice.id,
    }


