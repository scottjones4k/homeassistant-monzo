class AccountModel():
    id: str
    mask: str

    def __init__(self, account):
        self.id = account['id']
        self.mask = account['account_number'][-4:]

class WebhookModel():
    id: str
    account_id: str
    url: str

    def __init__(self, webhook):
        self.id = webhook['id']
        self.account_id = webhook['account_id']
        self.url = webhook['url']

class BaseMonzoModel():
    account_id: str
    mask: str
    balance: float
    currency: str
    spend_today: float

class BalanceModel(BaseMonzoModel):
    def __init__(self, account_id: str, mask: str, balance):
        self.account_id = account_id
        self.mask = mask
        self.balance = balance['balance']/100
        self.currency = balance['currency']
        self.spend_today = balance['spend_today']

class PotModel(BaseMonzoModel):
    id: str
    name: str

    def __init__(self, account_id: str, mask: str, pot):
        self.id = pot['id']
        self.mask = mask
        self.account_id = account_id
        self.name = pot['name']
        self.balance = pot['balance']/100
        self.currency = pot['currency']