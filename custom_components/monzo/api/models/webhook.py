from pydantic import BaseModel

class Webhook(BaseModel):
    id: str
    account_id: str
    url: str