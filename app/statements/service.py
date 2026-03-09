from datetime import date
from decimal import Decimal
import calendar
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.invoices.models import Invoice, InvoicePayment
from app.statements.models import StatementLock

def get_customer_statement(
    db: Session,
    customer_id: int,
    year: int,
    month: int,
):
    # Month boundaries
    month_start = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    month_end = date(year, month, last_day)

    # -----------------------------
    # Opening balance
    # -----------------------------
    invoices_before = (
        db.query(func.coalesce(func.sum(Invoice.total_amount), 0))
        .filter(
            Invoice.customer_id == customer_id,
            Invoice.is_account == True,
            Invoice.invoice_date < month_start,
        )
        .scalar()
    )

    payments_before = (
        db.query(func.coalesce(func.sum(InvoicePayment.amount), 0))
        .join(Invoice)
        .filter(
            Invoice.customer_id == customer_id,
            InvoicePayment.payment_date < month_start,
        )
        .scalar()
    )

    opening_balance = Decimal(invoices_before) - Decimal(payments_before)
    if opening_balance < 0:
        opening_balance = Decimal("0.00")

    # -----------------------------
    # Invoices this month
    # -----------------------------
    invoices = (
        db.query(Invoice)
        .filter(
            Invoice.customer_id == customer_id,
            Invoice.is_account == True,
            Invoice.invoice_date >= month_start,
            Invoice.invoice_date <= month_end,
        )
        .order_by(Invoice.invoice_date)
        .all()
    )

    invoices_total = sum(
        (inv.total_amount for inv in invoices),
        Decimal("0.00"),
    )

    # -----------------------------
    # Payments this month
    # -----------------------------
    payments_total = (
        db.query(func.coalesce(func.sum(InvoicePayment.amount), 0))
        .join(Invoice)
        .filter(
            Invoice.customer_id == customer_id,
            InvoicePayment.payment_date >= month_start,
            InvoicePayment.payment_date <= month_end,
        )
        .scalar()
    )

    payments_total = Decimal(payments_total)

    # -----------------------------
    # Closing balance
    # -----------------------------
    closing_balance = opening_balance + invoices_total - payments_total
    if closing_balance < 0:
        closing_balance = Decimal("0.00")

    return {
        "month_start": month_start,
        "month_end": month_end,
        "opening_balance": opening_balance,
        "invoices": invoices,
        "invoices_total": invoices_total,
        "payments_total": payments_total,
        "closing_balance": closing_balance,
    }



def is_statement_locked(db, customer_id: int, year: int, month: int) -> bool:
    return (
        db.query(StatementLock)
        .filter(
            StatementLock.customer_id == customer_id,
            StatementLock.year == year,
            StatementLock.month == month,
        )
        .first()
        is not None
    )
