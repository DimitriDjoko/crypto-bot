"""
config.py - Configuration centralisée du crypto trading bot
"""

# ─── Tokens à surveiller ───────────────────────────────────────────
TOKENS = [
    "bitcoin",
    "ethereum",
    "solana",
    "binancecoin",
    "ripple",
]

# IDs CoinGecko (doit correspondre à TOKENS)
COINGECKO_IDS = ",".join(TOKENS)

# ─── CoinGecko API ─────────────────────────────────────────────────
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
COINGECKO_CURRENCY = "usd"
REQUEST_TIMEOUT = 10      # secondes
RETRY_ATTEMPTS = 3
RETRY_DELAY = 5           # secondes entre chaque tentative

# ─── Base de données SQLite ────────────────────────────────────────
DB_PATH = "crypto_data.db"

# ─── Alertes (à configurer plus tard - Semaine 3) ──────────────────
DISCORD_WEBHOOK_URL = ""   # ex: https://discord.com/api/webhooks/...
GMAIL_SENDER = ""          # ex: monbot@gmail.com
GMAIL_PASSWORD = ""        # mot de passe application Gmail
GMAIL_RECIPIENT = ""       # ex: moi@email.com

# ─── Seuils pour les signaux ───────────────────────────────────────
# Variation de prix (%) qui déclenche une analyse IA
PRICE_CHANGE_THRESHOLD = 3.0    # +/- 3% sur 24h
VOLUME_SPIKE_THRESHOLD = 50.0   # +50% de volume vs moyenne

# ─── IA (Semaine 2) ────────────────────────────────────────────────
GEMINI_API_KEY = ""   # Gratuit sur https://aistudio.google.com
# Ou Claude API (payant mais meilleur)
ANTHROPIC_API_KEY = ""

# ─── Logging ───────────────────────────────────────────────────────
LOG_FILE = "bot.log"
LOG_LEVEL = "INFO"
