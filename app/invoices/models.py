from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    ForeignKey,
    Boolean,
    Numeric,
    DateTime,
)
from sqlalchemy.orm import relationship
from datetime import date, datetime

from app.core.database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)

    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)

    invoice_date = Column(Date, default=date.today)
    description = Column(String, nullable=True)

    total_amount = Column(Numeric(10, 2), nullable=False)

    is_account = Column(Boolean, default=False)
    is_paid = Column(Boolean, default=False)

    customer = relationship("Customer")


class InvoiceAttachment(Base):
    __tablename__ = "invoice_attachments"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)

    file_path = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    invoice = relationship("Invoice")

