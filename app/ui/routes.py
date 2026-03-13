from fastapi import APIRouter, Depends, Request, Form, UploadFile, File, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import func


from datetime import date
from decimal import Decimal
import os
from uuid import uuid4

from app.core.database import SessionLocal
from app.customers.models import Customer
from app.invoices.models import Invoice, InvoiceAttachment, InvoicePayment
from app.statements.models import StatementLock
from app.statements.service import get_customer_statement, is_statement_locked

router = APIRouter(prefix="/ui", tags=["ui"])
templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = "uploads/invoices"


# --------------------
# DB dependency
# --------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def require_login(request: Request):
    if not request.session.get("user"):
        return RedirectResponse("/login")
    return None


# --------------------
# Dashboard
# --------------------
@router.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db)):

    redirect = require_login(request)
    if redirect:
        return redirect

    today = date.today()
    month_start = date(today.year, today.month, 1)

    invoices_total = (
        db.query(func.coalesce(func.sum(Invoice.total_amount), 0))
        .filter(
            Invoice.is_account == True,
            Invoice.invoice_date >= month_start
        )
        .scalar()
    )

    payments_total = (
        db.query(func.coalesce(func.sum(InvoicePayment.amount), 0))
        .filter(
            InvoicePayment.payment_date >= month_start
        )
        .scalar()
    )

    total_outstanding = (
        db.query(func.coalesce(func.sum(Invoice.total_amount), 0))
        .filter(Invoice.is_account == True)
        .scalar()
    )

    total_payments = (
        db.query(func.coalesce(func.sum(InvoicePayment.amount), 0))
        .scalar()
    )

    total_outstanding = Decimal(total_outstanding) - Decimal(total_payments)

    customers_owing = (
        db.query(Customer)
        .join(Invoice)
        .group_by(Customer.id)
        .all()
    )

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "total_outstanding": total_outstanding,
            "invoices_total": invoices_total,
            "payments_total": payments_total,
            "customers_owing": customers_owing,
        },
    )


# --------------------
# Global Search
# --------------------

@router.get("/search")
def search(request: Request, q: str | None = None, db: Session = Depends(get_db)):

    redirect = require_login(request)
    if redirect:
        return redirect

    if not q:
        return templates.TemplateResponse(
            "search_results.html",
            {
                "request": request,
                "query": "",
                "customers": [],
                "invoices": [],
            },
        )

    customers = db.query(Customer).filter(
        Customer.name.ilike(f"%{q}%")
    ).all()

    phone_matches = db.query(Customer).filter(
        Customer.phone.ilike(f"%{q}%")
    ).all()

    invoices = db.query(Invoice).filter(
        Invoice.docket_number.ilike(f"%{q}%")
    ).all()

    invoice_number_matches = db.query(Invoice).filter(
        Invoice.invoice_number.ilike(f"%{q}%")
    ).all()

    invoice_id_match = []

    if q.isdigit():
        invoice = db.query(Invoice).filter(Invoice.id == int(q)).first()
        if invoice:
            invoice_id_match.append(invoice)

    customer_map = {c.id: c for c in customers + phone_matches}
    customers = list(customer_map.values())

    invoice_map = {
        i.id: i for i in invoices + invoice_id_match + invoice_number_matches
    }
    invoices = list(invoice_map.values())

    return templates.TemplateResponse(
        "search_results.html",
        {
            "request": request,
            "query": q,
            "customers": customers,
            "invoices": invoices,
        },
    )
# --------------------
# Customers
# --------------------
@router.get("/customers")
def customer_list(
    request: Request,
    message: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):

    redirect = require_login(request)
    if redirect:
        return redirect

    customers = db.query(Customer).order_by(Customer.name).all()

    for c in customers:

        invoices_total = (
            db.query(func.coalesce(func.sum(Invoice.total_amount), 0))
            .filter(
                Invoice.customer_id == c.id,
                Invoice.is_account == True,
            )
            .scalar()
        )

        payments_total = (
            db.query(func.coalesce(func.sum(InvoicePayment.amount), 0))
            .join(Invoice)
            .filter(Invoice.customer_id == c.id)
            .scalar()
        )

        balance = Decimal(invoices_total or 0) - Decimal(payments_total or 0)

        if balance < 0:
            balance = Decimal("0.00")

        c.balance = balance

    return templates.TemplateResponse(
        "customers.html",
        {
            "request": request,
            "customers": customers,
            "message": message,
            "error": error,
        },
    )

# --------------------
# Create Customer
# --------------------
@router.get("/customers/new")
def create_customer_form(request: Request):
    return templates.TemplateResponse(
        "create_customer.html",
        {"request": request},
    )
@router.post("/customers/new")
def create_customer_submit(
    request: Request,
    name: str = Form(...),
    phone: str | None = Form(None),
    is_account: bool = Form(False),
    db: Session = Depends(get_db),
):
    customer = Customer(
        name=name,
        phone=phone,
        is_account=is_account,
    )

    db.add(customer)
    db.commit()

    return RedirectResponse(
        url="/ui/customers?message=Customer created",
        status_code=303,
    )


# --------------------
# Customer Invoices
# --------------------
@router.get("/customers/{customer_id}/invoices")
def customer_invoices(
    customer_id: int,
    request: Request,
    message: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    invoices = (
        db.query(Invoice)
        .filter(Invoice.customer_id == customer_id)
        .order_by(Invoice.invoice_date.desc())
        .all()
    )

    return templates.TemplateResponse(
        "customer_invoices.html",
        {
            "request": request,
            "customer": customer,
            "invoices": invoices,
            "message": message,
            "error": error,
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

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

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
    docket_number: str | None = Form(None),
    description: str = Form(...),
    total_amount: Decimal = Form(...),
    is_account: bool = Form(False),
    db: Session = Depends(get_db),
):
    today = date.today()

    if is_statement_locked(db, customer_id, today.year, today.month):
        return RedirectResponse(
            url=f"/ui/customers/{customer_id}/invoices?error=Statement locked",
            status_code=303,
        )

    invoice = Invoice(
        customer_id=customer_id,
        docket_number=docket_number,
        description=description,
        total_amount=Decimal(total_amount),
        invoice_date=today,
        is_account=is_account,
    )

    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    return RedirectResponse(
        url=f"/ui/invoices/{invoice.id}?message=Invoice created",
        status_code=303,
    )


# --------------------
# Invoice Detail
# --------------------
@router.get("/invoices/{invoice_id}")
def invoice_detail(
    invoice_id: int,
    request: Request,
    error: str | None = None,
    message: str | None = None,
    db: Session = Depends(get_db),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    attachments = (
        db.query(InvoiceAttachment)
        .filter(InvoiceAttachment.invoice_id == invoice_id)
        .all()
    )

    return templates.TemplateResponse(
        "invoice_detail.html",
        {
            "request": request,
            "invoice": invoice,
            "attachments": attachments,
            "error": error,
            "message": message,
        },
    )


# --------------------
# Add Payment
# --------------------
@router.post("/invoices/{invoice_id}/payment")
def add_payment(
    invoice_id: int,
    amount: Decimal = Form(...),
    note: str | None = Form(None),
    db: Session = Depends(get_db),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    today = date.today()

    if is_statement_locked(db, invoice.customer_id, today.year, today.month):
        return RedirectResponse(
            url=f"/ui/invoices/{invoice_id}?error=Statement locked",
            status_code=303,
        )

    amount = Decimal(amount)

    if amount <= 0:
        return RedirectResponse(
            url=f"/ui/invoices/{invoice_id}?error=Invalid payment",
            status_code=303,
        )

    if amount > invoice.balance_due:
        return RedirectResponse(
            url=f"/ui/invoices/{invoice_id}?error=Payment exceeds balance",
            status_code=303,
        )

    payment = InvoicePayment(
        invoice_id=invoice_id,
        amount=amount,
        note=note,
    )

    db.add(payment)
    db.commit()

    return RedirectResponse(
        url=f"/ui/invoices/{invoice_id}?message=Payment added",
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

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

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
        raise HTTPException(status_code=404, detail="Invoice not found")

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid4()}{ext}"
    path = os.path.join(UPLOAD_DIR, filename)

    with open(path, "wb") as f:
        f.write(file.file.read())

    attachment = InvoiceAttachment(
        invoice_id=invoice_id,
        file_path=path,
    )

    db.add(attachment)
    db.commit()

    return RedirectResponse(
        url=f"/ui/invoices/{invoice_id}?message=File uploaded",
        status_code=303,
    )


# --------------------
# Monthly Statement
# --------------------
@router.get("/customers/{customer_id}/statement")
def customer_statement_ui(
    customer_id: int,
    year: int,
    month: int,
    request: Request,
    db: Session = Depends(get_db),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    statement = get_customer_statement(db, customer_id, year, month)

    locked = is_statement_locked(db, customer_id, year, month)

    prev_month = month - 1 or 12
    prev_year = year - 1 if month == 1 else year

    next_month = month + 1 if month < 12 else 1
    next_year = year + 1 if month == 12 else year

    return templates.TemplateResponse(
        "statement.html",
        {
            "request": request,
            "customer": customer,
            "year": year,
            "month": month,
            "locked": locked,
            "prev_year": prev_year,
            "prev_month": prev_month,
            "next_year": next_year,
            "next_month": next_month,
            **statement,
        },
    )


# --------------------
# Statement PDF
# --------------------
@router.get("/customers/{customer_id}/statement/pdf")
def customer_statement_pdf(
    customer_id: int,
    year: int,
    month: int,
    request: Request,
    db: Session = Depends(get_db),
):
    from weasyprint import HTML

    customer = db.query(Customer).filter(Customer.id == customer_id).first()

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    statement = get_customer_statement(db, customer_id, year, month)

    html = templates.get_template("statement_pdf.html").render({
        "customer": customer,
        "year": year,
        "month": month,
        **statement,
    })

    pdf = HTML(string=html).write_pdf()

    if not is_statement_locked(db, customer_id, year, month):
        db.add(
            StatementLock(
                customer_id=customer_id,
                year=year,
                month=month,
            )
        )
        db.commit()

    safe_name = customer.name.replace(" ", "_")

    filename = f"statement_{safe_name}_{year}_{month:02d}.pdf"

    return Response(
        pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )


# --------------------
# Lock Statement
# --------------------
@router.post("/customers/{customer_id}/statement/lock")
def lock_statement(
    customer_id: int,
    year: int = Form(...),
    month: int = Form(...),
    db: Session = Depends(get_db),
):
    existing = db.query(StatementLock).filter(
        StatementLock.customer_id == customer_id,
        StatementLock.year == year,
        StatementLock.month == month,
    ).first()

    if not existing:
        db.add(
            StatementLock(
                customer_id=customer_id,
                year=year,
                month=month,
            )
        )
        db.commit()

    return RedirectResponse(
        url=f"/ui/customers/{customer_id}/statement?year={year}&month={month}",
        status_code=303,
    )


# --------------------
# Unlock Statement
# --------------------
@router.post("/customers/{customer_id}/statement/unlock")
def unlock_statement(
    customer_id: int,
    year: int = Form(...),
    month: int = Form(...),
    db: Session = Depends(get_db),
):
    db.query(StatementLock).filter(
        StatementLock.customer_id == customer_id,
        StatementLock.year == year,
        StatementLock.month == month,
    ).delete()

    db.commit()

    return RedirectResponse(
        url=f"/ui/customers/{customer_id}/statement?year={year}&month={month}",
        status_code=303,
    )