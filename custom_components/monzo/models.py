class BaseMonzoModel():
    account_id: str
    balance: float
    currency: str

class BalanceModel(BaseMonzoModel):
    def __init__(self, account, balance):
        self.account_id = account['id']
        self.balance = balance['balance']
        self.currency = balance['currency']

class PotModel(BaseMonzoModel):
    id: str
    name: str

    def __init__(self, account, pot):
        self.id = pot['id']
        self.account_id = account['id']
        self.name = pot['name']
        self.balance = pot['balance']
        self.currency = pot['currency']