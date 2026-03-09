from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from app.ui.routes import router as ui_router

from app.core.database import Base, engine
from app.auth.routes import router as auth_router
from app.customers.models import Customer  # noqa: F401
from app.customers.routes import router as customer_router
from app.invoices.models import Invoice, InvoiceAttachment  # noqa: F401
from app.invoices.routes import router as invoice_router

app = FastAPI(title="Corbett Tyres Management System")
app.add_middleware(SessionMiddleware, secret_key="super-secret-key")
app.include_router(ui_router)
app.include_router(auth_router)


@app.on_event("startup")
def startup():
    # Create database tables
    Base.metadata.create_all(bind=engine)


app.include_router(customer_router)
app.include_router(invoice_router)


@app.get("/")
def health_check():
    return {"status": "ok"}
