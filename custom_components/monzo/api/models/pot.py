from pydantic import BaseModel

class Pot(BaseModel):
    id: str
    account_id: str = "Account"
    name: str
    balance: float
    currency: str
    goal_amount: float = 0
    deleted: bool
    locked: bool
    type: str
    cover_image_url: str