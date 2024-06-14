from pydantic import BaseModel

class Balance(BaseModel):
    balance: float
    currency: str
    spend_today: float
    total_balance: float