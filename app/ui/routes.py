from fastapi import APIRouter, Depends, Request, Form, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import date
import os
from uuid import uuid4

from app.core.database import SessionLocal
from app.customers.models import Customer
from app.invoices.models import Invoice, InvoiceAttachment

router = APIRouter(prefix="/ui", tags=["ui"])

templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = "uploads/invoices"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --------------------
# Customers
# --------------------
@router.get("/customers")
def customer_list(
    request: Request,
    message: str | None = None,
    db: Session = Depends(get_db),
):
    customers = db.query(Customer).order_by(Customer.name).all()
    return templates.TemplateResponse(
        "customers.html",
        {
            "request": request,
            "customers": customers,
            "message": message,
        },
    )


# --------------------
# Create Invoice
# --------------------
@router.get("/customers/{customer_id}/invoice")
def create_invoice_form(
    customer_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    return templates.TemplateResponse(
        "create_invoice.html",
        {
            "request": request,
            "customer": customer,
        },
    )


@router.post("/customers/{customer_id}/invoice")
def create_invoice_submit(
    customer_id: int,
    description: str = Form(...),
    total_amount: float = Form(...),
    is_account: bool = Form(False),
    db: Session = Depends(get_db),
):
    invoice = Invoice(
        customer_id=customer_id,
        description=description,
        total_amount=total_amount,
        invoice_date=date.today(),
        is_account=is_account,
        is_paid=False,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    # Redirect straight to upload page (Option A)
    return RedirectResponse(
        url=f"/ui/invoices/{invoice.id}/upload",
        status_code=303,
    )


# --------------------
# Upload Invoice Photo
# --------------------
@router.get("/invoices/{invoice_id}/upload")
def upload_invoice_form(
    invoice_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    customer = db.query(Customer).filter(Customer.id == invoice.customer_id).first()

    return templates.TemplateResponse(
        "upload_invoice.html",
        {
            "request": request,
            "invoice": invoice,
            "customer": customer,
        },
    )


@router.post("/invoices/{invoice_id}/upload")
def upload_invoice_submit(
    invoice_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        return {"error": "Invoice not found"}

    if not os.path.isdir(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR, exist_ok=True)


    ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid4()}{ext}"
    path = os.path.join(UPLOAD_DIR, filename)

    with open(path, "wb") as f:
        f.write(file.file.read())
