"""
storage.py - Sauvegarde des prix en base SQLite (gratuit, local)
Alternative gratuite à Azure CosmosDB
"""

import sqlite3
import logging
from datetime import datetime, timezone
from config import DB_PATH

logger = logging.getLogger(__name__)


def init_db():
    """Crée les tables si elles n'existent pas encore."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            token       TEXT NOT NULL,
            price_usd   REAL NOT NULL,
            market_cap  REAL,
            volume_24h  REAL,
            change_24h  REAL,
            timestamp   TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            token       TEXT NOT NULL,
            signal      TEXT NOT NULL,       -- BUY / SELL / HOLD
            confidence  REAL,                -- 0.0 à 1.0
            reason      TEXT,
            timestamp   TEXT NOT NULL
        )
    """)

    # Index pour accélérer les requêtes par token et date
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_prices_token ON prices(token)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_prices_ts    ON prices(timestamp)")

    conn.commit()
    conn.close()
    logger.info("✅ Base de données initialisée : %s", DB_PATH)


def save_prices(price_data: list[dict]):
    """
    Sauvegarde une liste de prix en base.

    Args:
        price_data: liste de dicts avec clés:
            token, price_usd, market_cap, volume_24h, change_24h
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    timestamp = datetime.now(timezone.utc).isoformat()

    rows = [
        (
            p["token"],
            p["price_usd"],
            p.get("market_cap"),
            p.get("volume_24h"),
            p.get("change_24h"),
            timestamp,
        )
        for p in price_data
    ]

    cursor.executemany(
        "INSERT INTO prices (token, price_usd, market_cap, volume_24h, change_24h, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )

    conn.commit()
    conn.close()
    logger.info("💾 %d prix sauvegardés à %s", len(rows), timestamp)


def save_signal(token: str, signal: str, confidence: float, reason: str):
    """Sauvegarde un signal de trading généré par l'IA."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO signals (token, signal, confidence, reason, timestamp) VALUES (?, ?, ?, ?, ?)",
        (token, signal, confidence, reason, datetime.now(timezone.utc).isoformat()),
    )

    conn.commit()
    conn.close()
    logger.info("📊 Signal sauvegardé : %s → %s (confiance: %.0f%%)", token, signal, confidence * 100)


def get_recent_prices(token: str, limit: int = 24) -> list[dict]:
    """
    Récupère les N derniers prix d'un token.

    Args:
        token: identifiant CoinGecko (ex: 'bitcoin')
        limit: nombre de lignes à retourner

    Returns:
        Liste de dicts triés du plus récent au plus ancien
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM prices WHERE token = ? ORDER BY timestamp DESC LIMIT ?",
        (token, limit),
    )

    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_all_latest_prices() -> list[dict]:
    """Retourne le prix le plus récent pour chaque token."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT p.*
        FROM prices p
        INNER JOIN (
            SELECT token, MAX(timestamp) AS max_ts
            FROM prices
            GROUP BY token
        ) latest ON p.token = latest.token AND p.timestamp = latest.max_ts
    """)

    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_recent_signals(limit: int = 10) -> list[dict]:
    """Retourne les N derniers signaux générés."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM signals ORDER BY timestamp DESC LIMIT ?",
        (limit,),
    )

    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows
