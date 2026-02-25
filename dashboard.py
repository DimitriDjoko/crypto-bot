"""
dashboard.py - Dashboard de monitoring du crypto trading bot
Semaine 3 : visualisation des prix et signaux en temps réel
Lancement : streamlit run dashboard.py
"""

import sqlite3
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timezone
from pathlib import Path
from storage import get_recent_prices, get_all_latest_prices, get_recent_signals
from config import DB_PATH, TOKENS

# ─── Configuration de la page ──────────────────────────────────────
st.set_page_config(
    page_title="Crypto Bot Monitor",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── CSS personnalisé ──────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500&display=swap');

  html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #0a0e17;
    color: #e2e8f0;
  }

  .main { background-color: #0a0e17; }

  h1, h2, h3 {
    font-family: 'Space Mono', monospace !important;
  }

  /* Metric cards */
  [data-testid="metric-container"] {
    background: linear-gradient(135deg, #111827 0%, #1a2235 100%);
    border: 1px solid #1e3a5f;
    border-radius: 12px;
    padding: 16px !important;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
  }

  [data-testid="metric-container"] > div {
    color: #94a3b8 !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.7rem !important;
    text-transform: uppercase;
    letter-spacing: 0.1em;
  }

  [data-testid="stMetricValue"] {
    color: #f0f4ff !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 1.4rem !important;
  }

  [data-testid="stMetricDelta"] svg { display: none; }

  /* Signal badges */
  .signal-buy {
    background: linear-gradient(135deg, #064e3b, #065f46);
    border: 1px solid #10b981;
    color: #6ee7b7;
    padding: 4px 14px;
    border-radius: 20px;
    font-family: 'Space Mono', monospace;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.05em;
  }
  .signal-sell {
    background: linear-gradient(135deg, #7f1d1d, #991b1b);
    border: 1px solid #ef4444;
    color: #fca5a5;
    padding: 4px 14px;
    border-radius: 20px;
    font-family: 'Space Mono', monospace;
    font-size: 0.75rem;
    font-weight: 700;
  }
  .signal-hold {
    background: linear-gradient(135deg, #1e3a5f, #1e40af);
    border: 1px solid #3b82f6;
    color: #93c5fd;
    padding: 4px 14px;
    border-radius: 20px;
    font-family: 'Space Mono', monospace;
    font-size: 0.75rem;
    font-weight: 700;
  }

  /* Header */
  .dashboard-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    border: 1px solid #1e3a5f;
    border-radius: 16px;
    padding: 24px 32px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .header-title {
    font-family: 'Space Mono', monospace;
    font-size: 1.5rem;
    font-weight: 700;
    color: #38bdf8;
    letter-spacing: -0.02em;
  }

  .header-subtitle {
    font-size: 0.8rem;
    color: #64748b;
    margin-top: 4px;
  }

  .status-dot {
    width: 10px;
    height: 10px;
    background: #10b981;
    border-radius: 50%;
    display: inline-block;
    margin-right: 8px;
    animation: pulse 2s infinite;
  }

  @keyframes pulse {
    0% { box-shadow: 0 0 0 0 rgba(16,185,129,0.4); }
    70% { box-shadow: 0 0 0 8px rgba(16,185,129,0); }
    100% { box-shadow: 0 0 0 0 rgba(16,185,129,0); }
  }

  /* Tableau signals */
  .signal-row {
    background: #111827;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 14px 20px;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  /* Streamlit overrides */
  .stSelectbox > div { background: #111827 !important; }
  div[data-baseweb="select"] { background: #111827 !important; }
  .stPlotlyChart { border-radius: 12px; overflow: hidden; }

  footer { display: none; }
  #MainMenu { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ─── Helpers ───────────────────────────────────────────────────────

def load_prices_df(token: str, limit: int = 48) -> pd.DataFrame:
    """Charge l'historique des prix d'un token en DataFrame."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT * FROM prices WHERE token = ? ORDER BY timestamp DESC LIMIT ?",
        conn, params=(token, limit)
    )
    conn.close()
    if df.empty:
        return df
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="mixed", utc=True)
    df = df.sort_values("timestamp")
    return df


def load_signals_df(limit: int = 50) -> pd.DataFrame:
    """Charge les derniers signaux en DataFrame."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT * FROM signals ORDER BY timestamp DESC LIMIT ?",
        conn, params=(limit,)
    )
    conn.close()
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"], format="mixed", utc=True)
    return df


def signal_badge(signal: str) -> str:
    cls = {"BUY": "signal-buy", "SELL": "signal-sell"}.get(signal, "signal-hold")
    return f'<span class="{cls}">{signal}</span>'


def format_price(price: float) -> str:
    if price >= 1000:
        return f"${price:,.0f}"
    elif price >= 1:
        return f"${price:,.2f}"
    else:
        return f"${price:.4f}"


def db_exists() -> bool:
    return Path(DB_PATH).exists()


# ─── Chart prix ────────────────────────────────────────────────────

def price_chart(df: pd.DataFrame, token: str) -> go.Figure:
    """Graphique en chandelier ou ligne selon les données disponibles."""
    fig = go.Figure()

    # Ligne principale
    fig.add_trace(go.Scatter(
        x=df["timestamp"],
        y=df["price_usd"],
        mode="lines",
        name=token.upper(),
        line=dict(color="#38bdf8", width=2),
        fill="tozeroy",
        fillcolor="rgba(56,189,248,0.05)",
        hovertemplate="<b>%{x|%d %b %H:%M}</b><br>$%{y:,.2f}<extra></extra>",
    ))

    # Points de variation notable
    notable = df[df["change_24h"].abs() >= 3]
    if not notable.empty:
        fig.add_trace(go.Scatter(
            x=notable["timestamp"],
            y=notable["price_usd"],
            mode="markers",
            marker=dict(color="#f59e0b", size=8, symbol="circle"),
            name="Variation >3%",
            hovertemplate="<b>%{x|%d %b %H:%M}</b><br>$%{y:,.2f}<extra></extra>",
        ))

    fig.update_layout(
        plot_bgcolor="#0a0e17",
        paper_bgcolor="#0a0e17",
        font=dict(family="DM Sans", color="#94a3b8"),
        margin=dict(l=0, r=0, t=10, b=0),
        height=280,
        showlegend=False,
        xaxis=dict(
            showgrid=False,
            showline=False,
            tickfont=dict(size=11, color="#475569"),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#1e293b",
            showline=False,
            tickfont=dict(size=11, color="#475569"),
            tickprefix="$",
        ),
        hovermode="x unified",
    )
    return fig


def confidence_chart(signals_df: pd.DataFrame) -> go.Figure:
    """Bar chart de la confiance moyenne par token."""
    if signals_df.empty:
        return go.Figure()

    avg = (
        signals_df.groupby("token")["confidence"]
        .mean()
        .reset_index()
        .sort_values("confidence", ascending=True)
    )
    avg["pct"] = (avg["confidence"] * 100).round(1)

    colors = []
    for _, row in avg.iterrows():
        last_signal = signals_df[signals_df["token"] == row["token"]].iloc[0]["signal"]
        colors.append(
            "#10b981" if last_signal == "BUY"
            else "#ef4444" if last_signal == "SELL"
            else "#3b82f6"
        )

    fig = go.Figure(go.Bar(
        x=avg["pct"],
        y=avg["token"].str.upper(),
        orientation="h",
        marker_color=colors,
        text=[f"{v}%" for v in avg["pct"]],
        textposition="outside",
        textfont=dict(color="#94a3b8", size=11),
        hovertemplate="<b>%{y}</b><br>Confiance: %{x:.1f}%<extra></extra>",
    ))

    fig.update_layout(
        plot_bgcolor="#0a0e17",
        paper_bgcolor="#0a0e17",
        font=dict(family="DM Sans", color="#94a3b8"),
        margin=dict(l=0, r=40, t=10, b=0),
        height=220,
        xaxis=dict(
            showgrid=True,
            gridcolor="#1e293b",
            range=[0, 110],
            ticksuffix="%",
            tickfont=dict(size=11, color="#475569"),
        ),
        yaxis=dict(
            showgrid=False,
            tickfont=dict(size=12, color="#e2e8f0"),
        ),
    )
    return fig


# ─── Layout principal ──────────────────────────────────────────────

def main():
    # Vérification DB
    if not db_exists():
        st.error("Base de données introuvable. Lance d'abord `python fetch_prices.py`.")
        st.stop()

    # Header
    now = datetime.now(timezone.utc).strftime("%d %b %Y — %H:%M UTC")
    st.markdown(f"""
    <div class="dashboard-header">
        <div>
            <div class="header-title">📡 CRYPTO BOT MONITOR</div>
            <div class="header-subtitle">Signaux IA — Gemini 2.5 Flash Lite</div>
        </div>
        <div style="text-align:right">
            <div style="font-family:'Space Mono',monospace; font-size:0.8rem; color:#38bdf8">
                <span class="status-dot"></span>LIVE
            </div>
            <div style="font-size:0.75rem; color:#475569; margin-top:4px">{now}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Charger les données
    latest_prices = get_all_latest_prices()
    signals_df    = load_signals_df(limit=50)

    if not latest_prices:
        st.warning("Aucune donnée de prix. Lance d'abord fetch_prices.py.")
        st.stop()

    # ── Section 1 : Métriques actuelles ──────────────────────────
    st.markdown("### Prix actuels")
    cols = st.columns(len(latest_prices))

    for i, price in enumerate(latest_prices):
        with cols[i]:
            change = price.get("change_24h") or 0
            delta_str = f"{change:+.2f}%"
            st.metric(
                label=price["token"].upper(),
                value=format_price(price["price_usd"]),
                delta=delta_str,
            )

    st.divider()

    # ── Section 2 : Graphique prix + Derniers signaux ─────────────
    col_chart, col_signals = st.columns([3, 2], gap="large")

    with col_chart:
        st.markdown("### Evolution du prix")

        token_labels = {t: t.upper() for t in TOKENS}
        selected = st.selectbox(
            "Token",
            options=TOKENS,
            format_func=lambda x: x.upper(),
            label_visibility="collapsed",
        )

        df_prices = load_prices_df(selected, limit=48)
        if not df_prices.empty:
            st.plotly_chart(price_chart(df_prices, selected), use_container_width=True)
            st.caption(f"{len(df_prices)} points de données — mise à jour toutes les heures")
        else:
            st.info(f"Pas encore assez de données pour {selected.upper()}.")

    with col_signals:
        st.markdown("### Derniers signaux IA")

        if signals_df.empty:
            st.info("Aucun signal généré pour l'instant.")
        else:
            # Afficher les 8 derniers signaux
            for _, row in signals_df.head(8).iterrows():
                badge = signal_badge(row["signal"])
                conf  = int(row["confidence"] * 100)
                ts    = row["timestamp"].strftime("%d/%m %H:%M")
                reason_short = row["reason"][:60] + "..." if len(row["reason"]) > 60 else row["reason"]

                st.markdown(f"""
                <div class="signal-row">
                    <div>
                        <div style="font-family:'Space Mono',monospace; font-size:0.85rem; color:#f0f4ff">
                            {row['token'].upper()}
                        </div>
                        <div style="font-size:0.72rem; color:#475569; margin-top:2px">{ts}</div>
                    </div>
                    <div style="text-align:center">
                        {badge}
                        <div style="font-size:0.7rem; color:#64748b; margin-top:4px">{conf}%</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    st.divider()

    # ── Section 3 : Confiance moyenne + Historique complet ────────
    col_conf, col_hist = st.columns([2, 3], gap="large")

    with col_conf:
        st.markdown("### Confiance moyenne par token")
        if not signals_df.empty:
            st.plotly_chart(confidence_chart(signals_df), use_container_width=True)
        else:
            st.info("Pas encore de signaux.")

    with col_hist:
        st.markdown("### Historique complet des signaux")
        if not signals_df.empty:
            display_df = signals_df.copy()
            display_df["timestamp"] = display_df["timestamp"].dt.strftime("%d/%m/%Y %H:%M")
            display_df["confidence"] = (display_df["confidence"] * 100).round(0).astype(int).astype(str) + "%"
            display_df = display_df[["timestamp", "token", "signal", "confidence", "reason"]].rename(columns={
                "timestamp":  "Date",
                "token":      "Token",
                "signal":     "Signal",
                "confidence": "Confiance",
                "reason":     "Raison",
            })
            display_df["Token"] = display_df["Token"].str.upper()

            st.dataframe(
                display_df,
                use_container_width=True,
                height=220,
                hide_index=True,
            )
        else:
            st.info("Pas encore de signaux.")

    # ── Footer ───────────────────────────────────────────────────
    st.markdown("""
    <div style="text-align:center; padding:24px 0 8px; font-size:0.72rem; color:#334155;
                font-family:'Space Mono',monospace; border-top:1px solid #1e293b; margin-top:24px">
        CRYPTO BOT MONITOR — Les signaux sont indicatifs uniquement. Ne constitue pas un conseil financier.
    </div>
    """, unsafe_allow_html=True)

    # Auto-refresh toutes les 5 minutes
    st.markdown("""
    <script>
        setTimeout(function() { window.location.reload(); }, 300000);
    </script>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
