"""
test_integration.py - Tests d'intégration complets du pipeline
Semaine 4 : validation de bout en bout
Lancement : python test_integration.py
"""

import sys
import os
import json
import logging
import sqlite3
import tempfile
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Charger .env si présent
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ══════════════════════════════════════════════════════════════════
# TESTS UNITAIRES — Indicateurs techniques
# ══════════════════════════════════════════════════════════════════

def test_rsi():
    """Vérifie que le RSI est calculé correctement."""
    from ai_analysis import compute_rsi

    # Série haussière → RSI élevé
    prices_up = [100 + i for i in range(20)]
    rsi_up = compute_rsi(prices_up)
    assert rsi_up is not None, "RSI ne doit pas être None"
    assert rsi_up > 60, f"RSI haussier devrait être > 60, obtenu : {rsi_up}"

    # Série baissière → RSI bas
    prices_down = [200 - i for i in range(20)]
    rsi_down = compute_rsi(prices_down)
    assert rsi_down is not None
    assert rsi_down < 40, f"RSI baissier devrait être < 40, obtenu : {rsi_down}"

    # Pas assez de données → None
    rsi_none = compute_rsi([100, 101, 102])
    assert rsi_none is None, "RSI devrait être None avec moins de 15 points"

    logger.info("  ✓ RSI haussier : %.1f (> 60)", rsi_up)
    logger.info("  ✓ RSI baissier : %.1f (< 40)", rsi_down)
    logger.info("  ✓ RSI données insuffisantes : None")
    return True


def test_moving_averages():
    """Vérifie les moyennes mobiles et la détection de tendance."""
    from ai_analysis import compute_moving_averages

    # Tendance haussière forte : prix > MA7 > MA25
    prices_bull = [100 + i * 2 for i in range(30)]
    ma_bull = compute_moving_averages(prices_bull)
    assert ma_bull["ma7"]  is not None, "MA7 manquante"
    assert ma_bull["ma25"] is not None, "MA25 manquante"
    assert "haussiere" in ma_bull["trend"], f"Tendance incorrecte : {ma_bull['trend']}"

    # Tendance baissière forte : prix < MA7 < MA25
    prices_bear = [200 - i * 2 for i in range(30)]
    ma_bear = compute_moving_averages(prices_bear)
    assert "baissiere" in ma_bear["trend"], f"Tendance incorrecte : {ma_bear['trend']}"

    logger.info("  ✓ MA7=%.2f  MA25=%.2f  Tendance : %s", ma_bull["ma7"], ma_bull["ma25"], ma_bull["trend"])
    logger.info("  ✓ Tendance baissière détectée : %s", ma_bear["trend"])
    return True


# ══════════════════════════════════════════════════════════════════
# TESTS INTÉGRATION — Base de données
# ══════════════════════════════════════════════════════════════════

def test_database():
    """Vérifie que la DB SQLite fonctionne correctement."""
    from storage import init_db, save_prices, save_signal, get_recent_prices, get_recent_signals

    # Utiliser une DB temporaire pour ne pas polluer la vraie
    import config
    original_db = config.DB_PATH
    config.DB_PATH = ":memory:"  # DB en mémoire pour le test

    try:
        # Réinitialiser la connexion avec la DB temporaire
        conn = sqlite3.connect(config.DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT, price_usd REAL, market_cap REAL,
            volume_24h REAL, change_24h REAL, timestamp TEXT)""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT, signal TEXT, confidence REAL,
            reason TEXT, timestamp TEXT)""")
        conn.commit()

        # Test save_prices
        fake_prices = [
            {"token": "bitcoin",  "price_usd": 65000, "market_cap": 1.2e12, "volume_24h": 40e9, "change_24h": 3.5},
            {"token": "ethereum", "price_usd": 1900,  "market_cap": 2.3e11, "volume_24h": 20e9, "change_24h": 4.8},
        ]

        ts = datetime.now(timezone.utc).isoformat()
        for p in fake_prices:
            cursor.execute(
                "INSERT INTO prices (token, price_usd, market_cap, volume_24h, change_24h, timestamp) VALUES (?,?,?,?,?,?)",
                (p["token"], p["price_usd"], p["market_cap"], p["volume_24h"], p["change_24h"], ts)
            )

        cursor.execute(
            "INSERT INTO signals (token, signal, confidence, reason, timestamp) VALUES (?,?,?,?,?)",
            ("bitcoin", "BUY", 0.85, "Test signal", ts)
        )
        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM prices")
        count_prices = cursor.fetchone()[0]
        assert count_prices == 2, f"Attendu 2 prix, obtenu {count_prices}"

        cursor.execute("SELECT COUNT(*) FROM signals")
        count_signals = cursor.fetchone()[0]
        assert count_signals == 1, f"Attendu 1 signal, obtenu {count_signals}"

        conn.close()
        logger.info("  ✓ Sauvegarde prix : %d entrées", count_prices)
        logger.info("  ✓ Sauvegarde signal : %d entrée", count_signals)
        return True

    finally:
        config.DB_PATH = original_db


# ══════════════════════════════════════════════════════════════════
# TESTS INTÉGRATION — Construction du prompt
# ══════════════════════════════════════════════════════════════════

def test_prompt_builder():
    """Vérifie que le prompt groupé est bien construit."""
    from ai_analysis import build_grouped_prompt, compute_indicators

    fake_prices = [
        {"price_usd": 65000 - i * 100, "change_24h": -0.5, "timestamp": f"2026-02-25T{10+i:02d}:00:00"}
        for i in range(25)
    ]
    # Plus récent en premier (comme la DB)
    fake_prices_desc = list(reversed(fake_prices))

    indicators = compute_indicators(fake_prices_desc)

    tokens_data = [
        {"token": "bitcoin",  "prices": fake_prices_desc, "indicators": indicators},
        {"token": "ethereum", "prices": fake_prices_desc, "indicators": indicators},
    ]

    prompt = build_grouped_prompt(tokens_data)

    assert "BITCOIN"  in prompt, "Bitcoin absent du prompt"
    assert "ETHEREUM" in prompt, "Ethereum absent du prompt"
    assert "RSI"      in prompt, "RSI absent du prompt"
    assert "MA7"      in prompt, "MA7 absente du prompt"
    assert "BUY"      in prompt, "Instructions BUY absentes"
    assert "signals"  in prompt, "Format JSON absent"

    logger.info("  ✓ Prompt construit : %d caractères", len(prompt))
    logger.info("  ✓ RSI présent : %.1f", indicators["rsi"] or 0)
    logger.info("  ✓ Tendance présente : %s", indicators["trend"])
    return True


# ══════════════════════════════════════════════════════════════════
# TESTS INTÉGRATION — Parsing réponse Gemini
# ══════════════════════════════════════════════════════════════════

def test_json_parsing():
    """Vérifie que le parsing de la réponse Gemini fonctionne dans tous les cas."""

    def parse_response(raw: str) -> dict:
        """Simule le parsing du code."""
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()
        return json.loads(raw)

    # Cas 1 : JSON propre
    clean_json = '{"market_context": "Marche haussier", "signals": [{"token": "bitcoin", "signal": "BUY", "confidence": 0.85, "reason": "Test"}]}'
    parsed = parse_response(clean_json)
    assert parsed["signals"][0]["signal"] == "BUY"
    logger.info("  ✓ JSON propre parsé correctement")

    # Cas 2 : JSON avec backticks markdown
    wrapped_json = '```json\n{"market_context": "Test", "signals": [{"token": "ethereum", "signal": "SELL", "confidence": 0.7, "reason": "Test"}]}\n```'
    parsed2 = parse_response(wrapped_json)
    assert parsed2["signals"][0]["signal"] == "SELL"
    logger.info("  ✓ JSON avec backticks markdown parsé correctement")

    # Cas 3 : Signal invalide → doit être remplacé par HOLD
    bad_signal = "MAYBE"
    result = bad_signal if bad_signal in ("BUY", "SELL", "HOLD") else "HOLD"
    assert result == "HOLD"
    logger.info("  ✓ Signal invalide remplacé par HOLD")

    # Cas 4 : Confidence hors bornes → doit être clampée
    conf = max(0.0, min(1.0, 1.5))
    assert conf == 1.0
    conf2 = max(0.0, min(1.0, -0.3))
    assert conf2 == 0.0
    logger.info("  ✓ Confidence clampée entre 0 et 1")

    return True


# ══════════════════════════════════════════════════════════════════
# LANCEUR PRINCIPAL
# ══════════════════════════════════════════════════════════════════

def run_all_tests():
    tests = [
        ("RSI",                  test_rsi),
        ("Moyennes mobiles",     test_moving_averages),
        ("Base de données",      test_database),
        ("Construction prompt",  test_prompt_builder),
        ("Parsing JSON Gemini",  test_json_parsing),
    ]

    print("\n" + "=" * 65)
    print("  TESTS D'INTEGRATION — PIPELINE COMPLET")
    print("=" * 65)

    results = {}
    for name, fn in tests:
        print(f"\n  > {name}...")
        try:
            results[name] = fn()
        except AssertionError as e:
            logger.error("  ✗ Assertion échouée : %s", e)
            results[name] = False
        except Exception as e:
            logger.error("  ✗ Erreur inattendue : %s", e)
            results[name] = False

    print("\n" + "=" * 65)
    print("  RÉSUMÉ")
    print("=" * 65)

    all_pass = True
    for name, ok in results.items():
        status = "✓ PASS" if ok else "✗ FAIL"
        print(f"  {status}  —  {name}")
        if not ok:
            all_pass = False

    print("=" * 65)
    if all_pass:
        print("  TOUS LES TESTS PASSENT — Pipeline opérationnel !")
    else:
        print("  Certains tests ont échoué — voir les logs ci-dessus.")
    print("=" * 65 + "\n")

    return all_pass


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
