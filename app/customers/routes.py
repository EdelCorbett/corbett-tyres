from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.customers.models import Customer
from app.customers.schemas import CustomerCreate

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
