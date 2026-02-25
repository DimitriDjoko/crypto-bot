"""
ai_analysis.py - Analyse IA avec Gemini 2.0 Flash (gratuit)
Semaine 2 : génération de signaux BUY / SELL / HOLD
"""

import os
import json
import logging
from datetime import datetime, timezone
from google import genai
from google.genai import types
from storage import get_recent_prices, get_all_latest_prices, save_signal
from config import PRICE_CHANGE_THRESHOLD

logger = logging.getLogger(__name__)

# ─── Client Gemini ─────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = "gemini-2.0-flash"


def build_prompt(token: str, prices: list[dict]) -> str:
    """
    Construit le prompt envoyé à Gemini pour analyser un token.

    Args:
        token: identifiant du token (ex: 'bitcoin')
        prices: liste des N derniers prix depuis la DB

    Returns:
        Prompt formaté prêt à envoyer
    """
    if not prices:
        return ""

    latest = prices[0]
    price_usd   = latest.get("price_usd", 0)
    change_24h  = latest.get("change_24h", 0)
    volume_24h  = latest.get("volume_24h", 0)
    market_cap  = latest.get("market_cap", 0)

    # Historique des prix (du plus ancien au plus récent)
    history_lines = "\n".join([
        f"  - {p['timestamp'][:16]} UTC : ${p['price_usd']:,.2f} ({p.get('change_24h', 0):+.2f}%)"
        for p in reversed(prices)
    ])

    prompt = f"""Tu es un analyste crypto expert. Analyse les données suivantes et génère un signal de trading.

TOKEN : {token.upper()}
Prix actuel    : ${price_usd:,.2f}
Variation 24h  : {change_24h:+.2f}%
Volume 24h     : ${volume_24h:,.0f}
Market Cap     : ${market_cap:,.0f}

Historique récent (du plus ancien au plus récent) :
{history_lines}

INSTRUCTIONS :
1. Analyse la tendance, le momentum et le volume
2. Génère un signal parmi : BUY, SELL ou HOLD
3. Donne une confiance entre 0.0 et 1.0
4. Explique ton raisonnement en 2-3 phrases maximum

Réponds UNIQUEMENT avec ce JSON (aucun texte autour) :
{{
  "signal": "BUY" | "SELL" | "HOLD",
  "confidence": 0.0 à 1.0,
  "reason": "Ton explication courte ici"
}}"""

    return prompt


def analyze_token(token: str) -> dict | None:
    """
    Envoie les données d'un token à Gemini et récupère le signal.

    Args:
        token: identifiant CoinGecko du token

    Returns:
        Dict avec signal, confidence, reason — ou None si erreur
    """
    # Récupérer les 24 derniers prix (= 24h si collecte horaire)
    prices = get_recent_prices(token, limit=24)

    if not prices:
        logger.warning("Aucune donnée en base pour %s, analyse ignorée.", token)
        return None

    prompt = build_prompt(token, prices)
    if not prompt:
        return None

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)

        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,        # Réponses stables et cohérentes
                max_output_tokens=200,  # Signal court = moins de tokens = moins de coût
            ),
        )

        raw = response.text.strip()

        # Nettoyer si Gemini ajoute des backticks markdown
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        result = json.loads(raw)

        # Validation du résultat
        signal     = result.get("signal", "HOLD").upper()
        confidence = float(result.get("confidence", 0.5))
        reason     = result.get("reason", "")

        if signal not in ("BUY", "SELL", "HOLD"):
            signal = "HOLD"

        confidence = max(0.0, min(1.0, confidence))  # clamp entre 0 et 1

        logger.info(
            "Signal %s -> %s (confiance: %.0f%%) | %s",
            token.upper(), signal, confidence * 100, reason
        )

        return {
            "token":      token,
            "signal":     signal,
            "confidence": confidence,
            "reason":     reason,
        }

    except json.JSONDecodeError as e:
        logger.error("Impossible de parser la réponse Gemini pour %s : %s", token, e)
        logger.debug("Réponse brute : %s", raw if 'raw' in dir() else "N/A")
        return None
    except Exception as e:
        logger.error("Erreur lors de l'analyse de %s : %s", token, e)
        return None


def display_signals(signals: list[dict]):
    """Affiche un tableau récapitulatif des signaux dans le terminal."""
    print("\n" + "=" * 70)
    print(f"  SIGNAUX IA ({datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')})")
    print("=" * 70)
    print(f"  {'Token':<12} {'Signal':<8} {'Confiance':>10} {'Raison'}")
    print("-" * 70)

    for s in signals:
        signal = s["signal"]
        conf   = s["confidence"]

        # Indicateur visuel selon le signal
        if signal == "BUY":
            indicator = "[BUY] "
        elif signal == "SELL":
            indicator = "[SELL]"
        else:
            indicator = "[HOLD]"

        reason_short = s["reason"][:45] + "..." if len(s["reason"]) > 45 else s["reason"]

        print(
            f"  {s['token'].upper():<12} "
            f"{indicator:<8} "
            f"{conf * 100:>8.0f}%  "
            f"{reason_short}"
        )

    print("=" * 70 + "\n")


def run_analysis():
    """
    Point d'entrée : analyse tous les tokens en base et sauvegarde les signaux.
    Filtre intelligemment : n'analyse que les tokens avec une variation notable
    pour économiser les appels API.
    """
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY manquante ! Ajoutela dans tes secrets GitHub.")
        return

    logger.info("Demarrage de l analyse IA avec Gemini %s...", MODEL)

    latest_prices = get_all_latest_prices()
    if not latest_prices:
        logger.error("Aucune donnee en base. Lance d'abord fetch_prices.py.")
        return

    signals = []

    for price_row in latest_prices:
        token     = price_row["token"]
        change_24h = abs(price_row.get("change_24h") or 0)

        # Optimisation : n'analyse que si variation >= seuil (economie d'appels API)
        if change_24h >= PRICE_CHANGE_THRESHOLD:
            logger.info(
                "Variation de %.2f%% sur %s -> analyse IA...",
                change_24h, token.upper()
            )
            result = analyze_token(token)
        else:
            logger.info(
                "Variation de %.2f%% sur %s < seuil %.1f%% -> HOLD par defaut",
                change_24h, token.upper(), PRICE_CHANGE_THRESHOLD
            )
            result = {
                "token":      token,
                "signal":     "HOLD",
                "confidence": 0.5,
                "reason":     f"Variation trop faible ({change_24h:.2f}%) pour generer un signal.",
            }

        if result:
            # Sauvegarder en base
            save_signal(
                token      = result["token"],
                signal     = result["signal"],
                confidence = result["confidence"],
                reason     = result["reason"],
            )
            signals.append(result)

    # Afficher le recap
    if signals:
        display_signals(signals)

    logger.info("Analyse terminee. %d signaux generes.", len(signals))


if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("bot.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    run_analysis()
