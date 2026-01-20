from pydantic import BaseModel
from datetime import date
from decimal import Decimal


class InvoiceCreate(BaseModel):
    customer_id: int
    invoice_date: date | None = None
    description: str | None = None
    total_amount: Decimal
    is_account: bool = False
