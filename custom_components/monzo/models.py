class AccountModel():
    id: str
    mask: str
    name: str

    def __init__(self, account):
        self.id = account['id']
        self.mask = account['account_number'][-4:]
        self.name = self.mask

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
    name: str
    balance: float
    currency: str

class BalanceModel(BaseMonzoModel):
    spend_today: float
    total_balance: float

    def __init__(self, account_id: str, mask: str, balance):
        self.account_id = account_id
        self.mask = mask
        self.name = mask
        self.balance = balance['balance']/100
        self.total_balance = balance['total_balance']/100
        self.currency = balance['currency']
        self.spend_today = -1*balance['spend_today']/100

class PotModel(BaseMonzoModel):
    id: str
    name: str
    goal_amount: float
    deleted: bool
    locked: bool
    pot_type: str
    cover_image_url: str

    def __init__(self, account_id: str, mask: str, pot):
        self.id = pot['id']
        self.mask = mask
        self.account_id = account_id
        self.name = pot['name']
        self.balance = pot['balance']/100
        self.currency = pot['currency']
        self.goal_amount = None
        if 'goal_amount' in pot:
            self.goal_amount = pot.get('goal_amount')/100
        self.deleted = pot['deleted']
        self.locked = pot['locked']
        self.pot_type = pot['type']
        self.cover_image_url = pot['cover_image_url']