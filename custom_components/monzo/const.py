"""Constants used for Monzo."""

DOMAIN = "monzo"

OAUTH2_AUTHORIZE = "https://auth.monzo.com"
OAUTH2_TOKEN = "https://api.monzo.com/oauth2/token"

API_ENDPOINT = "https://api.monzo.com"

CONF_CLOUDHOOK_URL = "cloudhook_url"

WEBHOOK_UPDATE = f"{DOMAIN}_webhook_update"

SERVICE_POT_DEPOSIT = "pot_deposit"
SERVICE_POT_WITHDRAW = "pot_withdraw"
SERVICE_UPDATE = "update"