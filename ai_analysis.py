"""
ai_analysis.py - Analyse IA avec Gemini (appel groupé + indicateurs techniques)
Semaine 4 : optimisation quota + RSI + moyennes mobiles
"""

import os
import json
import time
import logging
from datetime import datetime, timezone
from storage import get_recent_prices, get_all_latest_prices, save_signal
from config import PRICE_CHANGE_THRESHOLD

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = "gemini-2.5-flash-lite"


# ══════════════════════════════════════════════════════════════════
# INDICATEURS TECHNIQUES
# ══════════════════════════════════════════════════════════════════

def compute_rsi(prices: list, period: int = 14):
    """
    RSI (Relative Strength Index).
    > 70 : surachat (SELL potentiel)
    < 30 : survente (BUY potentiel)
    """
    if len(prices) < period + 1:
        return None

    gains, losses = [], []
    for i in range(1, period + 1):
        delta = prices[-i] - prices[-i - 1]
        if delta >= 0:
            gains.append(delta)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(delta))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        return 100.0

    rs  = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)


def compute_moving_averages(prices: list) -> dict:
    """
    Moyennes mobiles MA7 et MA25.
    Prix > MA7 > MA25 : tendance haussière forte
    Prix < MA7 < MA25 : tendance baissière forte
    """
    result = {"ma7": None, "ma25": None, "trend": "neutre"}

    if len(prices) >= 7:
        result["ma7"] = round(sum(prices[-7:]) / 7, 4)
    if len(prices) >= 25:
        result["ma25"] = round(sum(prices[-25:]) / 25, 4)

    if result["ma7"] and result["ma25"]:
        current = prices[-1]
        if current > result["ma7"] > result["ma25"]:
            result["trend"] = "haussiere forte"
        elif current < result["ma7"] < result["ma25"]:
            result["trend"] = "baissiere forte"
        elif result["ma7"] > result["ma25"]:
            result["trend"] = "haussiere"
        else:
            result["trend"] = "baissiere"

    return result


def compute_indicators(prices_rows: list) -> dict:
    """Calcule RSI + moyennes mobiles + volatilité."""
    ordered      = list(reversed(prices_rows))
    price_values = [p["price_usd"] for p in ordered]

    rsi = compute_rsi(price_values)
    ma  = compute_moving_averages(price_values)

    changes    = [abs(p.get("change_24h") or 0) for p in ordered if p.get("change_24h")]
    volatility = round(sum(changes) / len(changes), 2) if changes else 0

    return {
        "rsi":        rsi,
        "ma7":        ma["ma7"],
        "ma25":       ma["ma25"],
        "trend":      ma["trend"],
        "volatility": volatility,
    }


# ══════════════════════════════════════════════════════════════════
# PROMPT GROUPÉ
# ══════════════════════════════════════════════════════════════════

def build_grouped_prompt(tokens_data: list) -> str:
    """1 seul prompt pour analyser tous les tokens simultanément."""
    sections = []

    for td in tokens_data:
        token      = td["token"]
        prices     = td["prices"]
        indicators = td["indicators"]

        if not prices:
            continue

        latest     = prices[0]
        price_usd  = latest.get("price_usd", 0)
        change_24h = latest.get("change_24h", 0)
        volume_24h = latest.get("volume_24h", 0)

        history = "\n".join([
            f"    {p['timestamp'][:16]} : ${p['price_usd']:,.4f} ({p.get('change_24h', 0):+.2f}%)"
            for p in list(reversed(prices))[-6:]
        ])

        rsi_str   = f"{indicators['rsi']:.1f}" if indicators["rsi"] else "N/A"
        rsi_interp = ""
        if indicators["rsi"]:
            if indicators["rsi"] > 70:
                rsi_interp = " -> SURACHAT"
            elif indicators["rsi"] < 30:
                rsi_interp = " -> SURVENTE"
            else:
                rsi_interp = " -> neutre"

        ma7_str  = f"${indicators['ma7']:,.4f}"  if indicators["ma7"]  else "N/A"
        ma25_str = f"${indicators['ma25']:,.4f}" if indicators["ma25"] else "N/A"

        sections.append(f"""
--- {token.upper()} ---
Prix actuel   : ${price_usd:,.4f}
Variation 24h : {change_24h:+.2f}%
Volume 24h    : ${volume_24h:,.0f}
RSI (14)      : {rsi_str}{rsi_interp}
MA7           : {ma7_str}
MA25          : {ma25_str}
Tendance MM   : {indicators['trend']}
Historique recent :
{history}""")

    tokens_list = ", ".join([td["token"].upper() for td in tokens_data])

    return f"""Tu es un analyste crypto expert. Analyse le marche et genere des signaux de trading.

CONTEXTE : Analyse comparative de {len(tokens_data)} tokens - cherche les correlations.

{"".join(sections)}

INSTRUCTIONS :
1. Analyse chaque token en tenant compte du contexte global
2. RSI > 70 = surachat (SELL), RSI < 30 = survente (BUY)
3. Prix > MA7 > MA25 = tendance haussiere confirmee
4. Signal : BUY, SELL ou HOLD
5. Confiance entre 0.0 et 1.0
6. Explication en 1-2 phrases par token

Reponds UNIQUEMENT avec ce JSON :
{{
  "market_context": "Analyse globale du marche en 1 phrase",
  "signals": [
    {{
      "token": "nom_token",
      "signal": "BUY",
      "confidence": 0.0,
      "reason": "Explication"
    }}
  ]
}}

Tokens : {tokens_list}"""


# ══════════════════════════════════════════════════════════════════
# ANALYSE PRINCIPALE
# ══════════════════════════════════════════════════════════════════

def run_analysis():
    """1 seul appel Gemini pour tous les tokens. Inclut RSI + moyennes mobiles."""
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY manquante !")
        return

    logger.info("Analyse IA groupee avec Gemini %s...", MODEL)

    latest_prices = get_all_latest_prices()
    if not latest_prices:
        logger.error("Aucune donnee en base.")
        return

    to_analyze   = []
    hold_results = []

    for price_row in latest_prices:
        token      = price_row["token"]
        change_24h = abs(price_row.get("change_24h") or 0)
        prices     = get_recent_prices(token, limit=25)

        if change_24h >= PRICE_CHANGE_THRESHOLD:
            indicators = compute_indicators(prices)
            to_analyze.append({
                "token":      token,
                "prices":     prices,
                "indicators": indicators,
            })
            logger.info(
                "%.2f%% sur %s -> analyse (RSI: %s | Tendance: %s)",
                change_24h, token.upper(),
                f"{indicators['rsi']:.1f}" if indicators["rsi"] else "N/A",
                indicators["trend"],
            )
        else:
            hold_results.append({
                "token":      token,
                "signal":     "HOLD",
                "confidence": 0.5,
                "reason":     f"Variation faible ({change_24h:.2f}%) sous le seuil de {PRICE_CHANGE_THRESHOLD}%.",
            })
            logger.info("%.2f%% sur %s < %.1f%% -> HOLD", change_24h, token.upper(), PRICE_CHANGE_THRESHOLD)

    # ── 1 seul appel Gemini ───────────────────────────────────────
    ai_results = []

    if to_analyze:
        prompt = build_grouped_prompt(to_analyze)
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=GEMINI_API_KEY)

            for attempt in range(3):
                try:
                    logger.info("Appel Gemini unique pour %d tokens...", len(to_analyze))
                    response = client.models.generate_content(
                        model=MODEL,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.2,
                            max_output_tokens=800,
                        ),
                    )
                    break
                except Exception as e:
                    if "429" in str(e) and attempt < 2:
                        wait = 35 * (attempt + 1)
                        logger.warning("Rate limit, attente %ds...", wait)
                        time.sleep(wait)
                    else:
                        raise

            raw = response.text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()

            parsed = json.loads(raw)

            market_context = parsed.get("market_context", "")
            if market_context:
                logger.info("Contexte marche : %s", market_context)

            for s in parsed.get("signals", []):
                signal     = s.get("signal", "HOLD").upper()
                confidence = float(s.get("confidence", 0.5))
                reason     = s.get("reason", "")

                if signal not in ("BUY", "SELL", "HOLD"):
                    signal = "HOLD"
                confidence = max(0.0, min(1.0, confidence))

                ai_results.append({
                    "token":      s.get("token", "").lower(),
                    "signal":     signal,
                    "confidence": confidence,
                    "reason":     reason,
                })
                logger.info(
                    "Signal %s -> %s (%.0f%%) | %s",
                    s.get("token", "").upper(), signal, confidence * 100, reason
                )

        except json.JSONDecodeError as e:
            logger.error("Parsing JSON echoue : %s", e)
        except Exception as e:
            logger.error("Erreur appel Gemini : %s", e)

    # ── Sauvegarder ───────────────────────────────────────────────
    all_signals = ai_results + hold_results

    for s in all_signals:
        save_signal(
            token      = s["token"],
            signal     = s["signal"],
            confidence = s["confidence"],
            reason     = s["reason"],
        )

    if all_signals:
        display_signals(all_signals)

    logger.info(
        "Analyse terminee : %d signaux, %d appel(s) Gemini.",
        len(all_signals),
        1 if to_analyze else 0,
    )

    try:
        from alerts import check_and_alert
        check_and_alert()
    except Exception as e:
        logger.error("Erreur alertes : %s", e)


def display_signals(signals: list):
    print("\n" + "=" * 75)
    print(f"  SIGNAUX IA ({datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')})")
    print("=" * 75)
    print(f"  {'Token':<14} {'Signal':<8} {'Confiance':>10}  {'Raison'}")
    print("-" * 75)

    for s in signals:
        indicator    = {"BUY": "[BUY] ", "SELL": "[SELL]"}.get(s["signal"], "[HOLD]")
        reason_short = s["reason"][:48] + "..." if len(s["reason"]) > 48 else s["reason"]
        print(
            f"  {s['token'].upper():<14} "
            f"{indicator:<8} "
            f"{s['confidence'] * 100:>8.0f}%  "
            f"{reason_short}"
        )

    print("=" * 75 + "\n")


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
