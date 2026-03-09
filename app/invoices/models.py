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
    invoice_number = Column(String, unique=True, index=True)
    
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)

    docket_number = Column(String, nullable=True, index=True)

    invoice_date = Column(Date, default=date.today)
    description = Column(String, nullable=True)

    total_amount = Column(Numeric(10, 2), nullable=False)
    is_account = Column(Boolean, default=False)

    customer = relationship("Customer")
    payments = relationship(
        "InvoicePayment",
        back_populates="invoice",
        cascade="all, delete-orphan",
    )

    # --------------------
    # Computed properties
    # --------------------
    @property
    def total_paid(self) -> float:
        return float(sum(p.amount for p in self.payments))

    @property
    def balance_due(self) -> float:
        return float(self.total_amount) - self.total_paid

    @property
    def payment_status(self) -> str:
        if self.balance_due <= 0:
            return "PAID"
        if self.total_paid > 0:
            return "PARTIAL"
        return "UNPAID"


class InvoiceAttachment(Base):
    __tablename__ = "invoice_attachments"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)

    file_path = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    invoice = relationship("Invoice")


class InvoicePayment(Base):
    __tablename__ = "invoice_payments"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)

    amount = Column(Numeric(10, 2), nullable=False)
    payment_date = Column(Date, default=date.today)
    note = Column(String, nullable=True)

    invoice = relationship("Invoice", back_populates="payments")
