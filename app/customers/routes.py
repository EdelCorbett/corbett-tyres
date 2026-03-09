from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from decimal import Decimal
import calendar

from app.core.database import SessionLocal
from app.customers.models import Customer
from app.customers.schemas import CustomerCreate
from app.invoices.models import Invoice

router = APIRouter(prefix="/customers", tags=["customers"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --------------------
# Customers
# --------------------
@router.post("/")
def create_customer(
    customer: CustomerCreate,
    db: Session = Depends(get_db),
):
    db_customer = Customer(**customer.model_dump())
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    return db_customer


@router.get("/")
def list_customers(db: Session = Depends(get_db)):
    return db.query(Customer).order_by(Customer.name).all()


@router.get("/search")
def search_customers(
    q: str,
    db: Session = Depends(get_db),
):
    return (
        db.query(Customer)
        .filter(
            (Customer.name.ilike(f"%{q}%"))
            | (Customer.phone.ilike(f"%{q}%"))
        )
        .all()
    )


# --------------------
# Customer Statement (WITH PREVIOUS BALANCE)
# --------------------
@router.get("/{customer_id}/statement")
def customer_statement(
    customer_id: int,
    year: int,
    month: int,
    db: Session = Depends(get_db),
):
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Month must be between 1 and 12")

    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    start_date = date(year, month, 1)
    end_date = date(year, month, calendar.monthrange(year, month)[1])

    # -----------------------------
    # 1️⃣ Previous balance (before month)
    # -----------------------------
    previous_invoices = (
        db.query(Invoice)
        .filter(
            Invoice.customer_id == customer_id,
            Invoice.is_account == True,
            Invoice.invoice_date < start_date,
        )
        .all()
    )

    opening_balance = Decimal("0.00")

    for inv in previous_invoices:
        paid = sum((p.amount for p in inv.payments), Decimal("0.00"))
        opening_balance += inv.total_amount - paid

    # -----------------------------
    # 2️⃣ This month’s invoices
    # -----------------------------
    month_invoices = (
        db.query(Invoice)
        .filter(
            Invoice.customer_id == customer_id,
            Invoice.is_account == True,
            Invoice.invoice_date >= start_date,
            Invoice.invoice_date <= end_date,
        )
        .order_by(Invoice.invoice_date)
        .all()
    )

    invoice_rows = []
    month_balance = Decimal("0.00")

    for inv in month_invoices:
        paid = sum((p.amount for p in inv.payments), Decimal("0.00"))
        balance = inv.total_amount - paid

        invoice_rows.append({
            "invoice_id": inv.id,
            "invoice_date": inv.invoice_date,
            "docket_number": inv.docket_number,
            "total": inv.total_amount,
            "paid": paid,
            "balance": balance,
        })

        month_balance += balance

    # -----------------------------
    # 3️⃣ Final totals
    # -----------------------------
    total_due = opening_balance + month_balance

    return {
        "customer_id": customer_id,
        "customer_name": customer.name,
        "period": f"{year}-{month:02d}",
        "opening_balance": opening_balance.quantize(Decimal("0.01")),
        "month_balance": month_balance.quantize(Decimal("0.01")),
        "total_due": total_due.quantize(Decimal("0.01")),
        "invoices": invoice_rows,
    }
