"""
fetch_prices.py - Collecte des prix crypto via CoinGecko API (gratuit)
Semaine 1 du roadmap : Data Collection
"""

import time
import logging
import requests
from datetime import datetime
from config import (
    COINGECKO_BASE_URL,
    COINGECKO_IDS,
    COINGECKO_CURRENCY,
    TOKENS,
    REQUEST_TIMEOUT,
    RETRY_ATTEMPTS,
    RETRY_DELAY,
    PRICE_CHANGE_THRESHOLD,
    LOG_FILE,
    LOG_LEVEL,
)
from storage import init_db, save_prices, get_all_latest_prices

# ─── Logging ───────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
# Fix encodage Windows : force UTF-8 sur le terminal
import sys
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
logger = logging.getLogger(__name__)


def fetch_prices_from_coingecko() -> list[dict] | None:
    """
    Récupère les prix depuis l'API CoinGecko (gratuite, sans clé).

    Returns:
        Liste de dicts avec les données de prix, ou None si erreur.
    """
    url = f"{COINGECKO_BASE_URL}/coins/markets"
    params = {
        "vs_currency": COINGECKO_CURRENCY,
        "ids": COINGECKO_IDS,
        "order": "market_cap_desc",
        "per_page": len(TOKENS),
        "page": 1,
        "sparkline": False,
        "price_change_percentage": "24h",
    }

    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            logger.info("🌐 Requête CoinGecko (tentative %d/%d)...", attempt, RETRY_ATTEMPTS)
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)

            # Gestion des rate limits (429)
            if response.status_code == 429:
                wait = int(response.headers.get("Retry-After", 60))
                logger.warning("⚠️  Rate limit atteint. Attente %ds...", wait)
                time.sleep(wait)
                continue

            response.raise_for_status()
            data = response.json()

            # Normalisation des données
            prices = []
            for coin in data:
                prices.append({
                    "token":      coin["id"],
                    "price_usd":  coin["current_price"],
                    "market_cap": coin.get("market_cap"),
                    "volume_24h": coin.get("total_volume"),
                    "change_24h": coin.get("price_change_percentage_24h"),
                    "symbol":     coin.get("symbol", "").upper(),
                    "name":       coin.get("name", ""),
                })

            logger.info("✅ %d tokens récupérés avec succès", len(prices))
            return prices

        except requests.exceptions.Timeout:
            logger.error("❌ Timeout sur la requête CoinGecko (tentative %d)", attempt)
        except requests.exceptions.ConnectionError:
            logger.error("❌ Erreur de connexion (tentative %d)", attempt)
        except requests.exceptions.HTTPError as e:
            logger.error("❌ Erreur HTTP %s (tentative %d)", e, attempt)
        except Exception as e:
            logger.error("❌ Erreur inattendue : %s", e)

        if attempt < RETRY_ATTEMPTS:
            logger.info("⏳ Nouvelle tentative dans %ds...", RETRY_DELAY)
            time.sleep(RETRY_DELAY)

    logger.critical("🚨 Impossible de récupérer les données après %d tentatives.", RETRY_ATTEMPTS)
    return None


def display_prices(prices: list[dict]):
    """Affiche un tableau récapitulatif dans le terminal."""
    print("\n" + "═" * 65)
    from datetime import timezone
    print(f"  CRYPTO PRICES  --  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("═" * 65)
    print(f"  {'Token':<12} {'Prix (USD)':>12} {'24h %':>9} {'Volume 24h':>15}")
    print("─" * 65)

    for p in prices:
        change = p.get("change_24h") or 0
        arrow = "▲" if change >= 0 else "▼"
        color_start = "\033[92m" if change >= 0 else "\033[91m"   # vert / rouge
        color_end = "\033[0m"

        volume = p.get("volume_24h") or 0
        volume_str = f"${volume/1_000_000:.1f}M" if volume >= 1_000_000 else f"${volume:,.0f}"

        print(
            f"  {p['symbol']:<12} "
            f"${p['price_usd']:>11,.2f} "
            f"{color_start}{arrow} {abs(change):>6.2f}%{color_end} "
            f"{volume_str:>15}"
        )

        # Alerte si variation importante
        if abs(change) >= PRICE_CHANGE_THRESHOLD:
            logger.info(
                "🚨 ALERTE : %s a bougé de %.2f%% en 24h → candidat pour analyse IA",
                p["symbol"], change
            )

    print("═" * 65 + "\n")


def run():
    """Point d'entrée principal : fetch → save → display."""
    logger.info("🤖 Démarrage du bot de collecte de prix...")

    # Initialiser la DB au premier lancement
    init_db()

    # Récupérer les prix
    prices = fetch_prices_from_coingecko()
    if not prices:
        logger.error("Arrêt : aucune donnée récupérée.")
        return

    # Sauvegarder en base
    save_prices(prices)

    # Afficher dans le terminal
    display_prices(prices)

    # Récap depuis la DB (pour vérifier que la sauvegarde fonctionne)
    latest = get_all_latest_prices()
    logger.info("📦 %d tokens en base de données.", len(latest))

    logger.info("✅ Collecte terminée avec succès.")


if __name__ == "__main__":
    run()
