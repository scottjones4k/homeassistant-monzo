from pydantic import BaseModel

CURRENT_ACCOUNT = "uk_retail"
ACCOUNT_NAMES = {
    CURRENT_ACCOUNT: "Current Account",
    "uk_retail_joint": "Joint Account",
    "uk_monzo_flex": "Flex",
    "uk_business": "Business Account",
    "uk_rewards": "Cashback",
}

class Account(BaseModel):
    id: str
    account_number: str
    type: str

    @property
    def mask(self):
        return self.account_number[-4:]
    
    @property
    def name(self):
        return ACCOUNT_NAMES.get(self.type, self.type)