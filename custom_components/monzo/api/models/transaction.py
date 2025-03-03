from typing import Literal, Dict
from pydantic import BaseModel

class Metadata(BaseModel):
    notes: str | None = None
    pot_id: str | None = None
    bills_pot_id: str | None = None
    triggered_by: str | None = None
    trigger: str | None = None
    tokenization_method: str | None = None

class AtmFeeDetailed(BaseModel):
    withdrawal_amount: int

class Counterparty(BaseModel):
    name: str | None = None
    account_number: str | None = None
    sort_code: str | None = None

class Transaction(BaseModel):
    account_id: str
    metadata: Metadata
    scheme: str
    atm_fee_detailed: AtmFeeDetailed | None = None
    counterparty: Counterparty | None = None
    amount: int
    description: str
    currency: str
    created: str
    id: str
    decline_reason: str | None = None
    categories: Dict[str, int] | None = None

class TransactionWrapper(BaseModel):
    type: Literal["transaction.created", "transaction.updated"]
    data: Transaction

