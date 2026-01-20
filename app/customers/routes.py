from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
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
    return db.query(Customer).all()


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


@router.get("/{customer_id}/statement")
def customer_statement(
    customer_id: int,
    year: int,
    month: int,
    db: Session = Depends(get_db),
):
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Month must be between 1 and 12")

    start_date = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end_date = date(year, month, last_day)

    invoices = (
        db.query(Invoice)
        .filter(
            Invoice.customer_id == customer_id,
            Invoice.is_account == True,
            Invoice.is_paid == False,
            Invoice.invoice_date >= start_date,
            Invoice.invoice_date <= end_date,
        )
        .order_by(Invoice.invoice_date)
        .all()
    )

    total = sum(inv.total_amount for inv in invoices)

    return {
        "customer_id": customer_id,
        "period": f"{year}-{month:02d}",
        "invoice_count": len(invoices),
        "total_due": total,
        "invoices": invoices,
    }
