from fastapi import FastAPI

from app.core.database import Base, engine
from app.customers.models import Customer  # noqa: F401
from app.customers.routes import router as customer_router
from app.invoices.models import Invoice, InvoiceAttachment  # noqa: F401
from app.invoices.routes import router as invoice_router

app = FastAPI(title="Corbett Tyres Management System")


@app.on_event("startup")
def startup():
    # Create database tables
    Base.metadata.create_all(bind=engine)


app.include_router(customer_router)
app.include_router(invoice_router)


@app.get("/")
def health_check():
    return {"status": "ok"}
