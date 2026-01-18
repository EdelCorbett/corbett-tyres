from pydantic import BaseModel

class CustomerCreate(BaseModel):
    name: str
    phone: str | None = None
    is_account: bool = False
