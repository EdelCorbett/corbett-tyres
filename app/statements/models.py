from sqlalchemy import Column, Integer, Date, ForeignKey, UniqueConstraint
from app.core.database import Base


class StatementLock(Base):
    __tablename__ = "statement_locks"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("customer_id", "month", "year", name="uq_statement_lock"),
    )
