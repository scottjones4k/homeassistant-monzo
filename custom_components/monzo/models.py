class AccountModel():
    id: str
    mask: str

    def __init__(self, account):
        self.id = account['id']
        self.mask = account['account_number'][-4:]

class BaseMonzoModel():
    account_id: str
    balance: float
    currency: str

class BalanceModel(BaseMonzoModel):
    def __init__(self, account_id: str, balance):
        self.account_id = account_id
        self.balance = balance['balance']
        self.currency = balance['currency']

class PotModel(BaseMonzoModel):
    id: str
    name: str

    def __init__(self, account_id: str, pot):
        self.id = pot['id']
        self.account_id = account_id
        self.name = pot['name']
        self.balance = pot['balance']
        self.currency = pot['currency']