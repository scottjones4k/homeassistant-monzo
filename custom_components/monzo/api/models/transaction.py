from typing import Literal
from pydantic import BaseModel

class Metadata(BaseModel):
    notes: str | None
    pot_id: str | None
    bills_pot_id: str | None
    triggered_by: str | None
    trigger: str | None
    tokenization_method: str | None

class AtmFeeDetailed(BaseModel):
    withdrawal_amount: int

class Counterparty(BaseModel):
    name: str | None
    account_number: str | None
    sort_code: str | None

class Transaction(BaseModel):
    account_id: str
    metadata: Metadata
    scheme: str
    atm_fee_detailed: AtmFeeDetailed | None
    counterparty: Counterparty | None
    amount: int
    description: str
    currency: str
    created: str
    id: str

class TransactionWrapper(BaseModel):
    type: Literal["transaction.created", "transaction.updated"]
    data: Transaction

