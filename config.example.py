"""
EVE Co-Pilot Configuration Template

Copy this file to config.py and fill in your credentials:
    cp config.example.py config.py
"""

# Database Configuration
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "eve_sde",
    "user": "eve",
    "password": "YOUR_DB_PASSWORD"
}

# ESI API Configuration
ESI_BASE_URL = "https://esi.evetech.net/latest"
ESI_USER_AGENT = "EVE-CoPilot/1.0"

# Common Region IDs
REGIONS = {
    "the_forge": 10000002,      # Jita
    "domain": 10000043,          # Amarr
    "heimatar": 10000030,        # Rens
    "sinq_laison": 10000032,     # Dodixie
    "metropolis": 10000042,      # Hek
}

# Server Configuration
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8000

# OAuth2 Configuration (EVE SSO)
# Register your application at: https://developers.eveonline.com/
EVE_SSO_CLIENT_ID = "YOUR_CLIENT_ID"
EVE_SSO_SECRET_KEY = "YOUR_SECRET_KEY"
EVE_SSO_CALLBACK_URL = "http://YOUR_SERVER_IP:8000/api/auth/callback"

# EVE SSO Endpoints
EVE_SSO_AUTH_URL = "https://login.eveonline.com/v2/oauth/authorize"
EVE_SSO_TOKEN_URL = "https://login.eveonline.com/v2/oauth/token"
EVE_SSO_VERIFY_URL = "https://esi.evetech.net/verify/"
EVE_SSO_JWKS_URL = "https://login.eveonline.com/oauth/jwks"

# Required ESI Scopes for Co-Pilot
ESI_SCOPES = [
    "esi-wallet.read_character_wallet.v1",
    "esi-assets.read_assets.v1",
    "esi-markets.read_character_orders.v1",
    "esi-skills.read_skills.v1",
    "esi-industry.read_character_jobs.v1",
    "esi-characters.read_blueprints.v1",
    "esi-wallet.read_corporation_wallets.v1",
    "esi-corporations.read_corporation_membership.v1",
    "esi-characters.read_corporation_roles.v1",
]

# Token Storage Path
TOKEN_STORAGE_PATH = "/path/to/eve_copilot/tokens.json"

# Discord Webhook Configuration (optional)
DISCORD_WEBHOOK_URL = ""

# Market Hunter Configuration
HUNTER_MIN_ROI = 15.0
HUNTER_MIN_PROFIT = 500000
HUNTER_TOP_CANDIDATES = 20
HUNTER_DEFAULT_ME = 10

# War Room Configuration
WAR_DATA_RETENTION_DAYS = 30
WAR_DOCTRINE_MIN_FLEET_SIZE = 10
WAR_HEATMAP_MIN_KILLS = 5
WAR_EVEREF_BASE_URL = "https://data.everef.net/killmails"

# Discord War Alerts
WAR_DISCORD_ENABLED = False
WAR_ALERT_DEMAND_SCORE_THRESHOLD = 2.0
WAR_ALERT_MIN_GAP_UNITS = 50

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN"  # Get from @BotFather
TELEGRAM_ALERTS_CHANNEL = "-100XXXXXXXXXXXXX"  # Channel ID for combat hotspot alerts
TELEGRAM_REPORTS_CHANNEL = "-100XXXXXXXXXXXXX"  # Channel ID for scheduled reports
TELEGRAM_ENABLED = False  # Set to True to enable Telegram notifications
