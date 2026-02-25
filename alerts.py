"""
alerts.py - Alertes email Gmail pour les signaux de trading
Semaine 3 : notifications automatiques BUY / SELL
"""

import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone
from storage import get_recent_signals

logger = logging.getLogger(__name__)

# ─── Config depuis les variables d'environnement ───────────────────
GMAIL_SENDER    = os.environ.get("GMAIL_SENDER", "")
GMAIL_PASSWORD  = os.environ.get("GMAIL_PASSWORD", "")
GMAIL_RECIPIENT = os.environ.get("GMAIL_RECIPIENT", "")

# Seuil de confiance minimum pour envoyer une alerte
CONFIDENCE_THRESHOLD = 0.70   # 70%

# Signaux qui déclenchent une alerte (pas HOLD)
ALERT_SIGNALS = {"BUY", "SELL"}


def build_email_html(signals: list[dict]) -> tuple[str, str]:
    """
    Construit le sujet et le corps HTML de l'email.

    Returns:
        (subject, html_body)
    """
    now = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")

    # Résumé pour le sujet
    signal_parts = [
        f"{s['token'].upper()} {s['signal']} ({int(s['confidence']*100)}%)"
        for s in signals
    ]
    subject = f"[Crypto Bot] {' | '.join(signal_parts)}"

    # Couleurs par signal
    colors = {
        "BUY":  {"bg": "#064e3b", "border": "#10b981", "text": "#6ee7b7", "label": "BUY"},
        "SELL": {"bg": "#7f1d1d", "border": "#ef4444", "text": "#fca5a5", "label": "SELL"},
        "HOLD": {"bg": "#1e3a5f", "border": "#3b82f6", "text": "#93c5fd", "label": "HOLD"},
    }

    # Construire les lignes de signaux
    rows_html = ""
    for s in signals:
        c = colors.get(s["signal"], colors["HOLD"])
        conf = int(s["confidence"] * 100)

        rows_html += f"""
        <tr>
            <td style="padding:16px 20px; border-bottom:1px solid #1e293b;">
                <span style="font-family:'Courier New',monospace; font-size:16px;
                             font-weight:700; color:#f0f4ff;">
                    {s['token'].upper()}
                </span>
            </td>
            <td style="padding:16px 20px; border-bottom:1px solid #1e293b; text-align:center;">
                <span style="background:{c['bg']}; border:1px solid {c['border']};
                             color:{c['text']}; padding:4px 16px; border-radius:20px;
                             font-family:'Courier New',monospace; font-size:13px; font-weight:700;">
                    {c['label']}
                </span>
            </td>
            <td style="padding:16px 20px; border-bottom:1px solid #1e293b; text-align:center;">
                <span style="font-family:'Courier New',monospace; font-size:15px; color:#38bdf8;">
                    {conf}%
                </span>
            </td>
            <td style="padding:16px 20px; border-bottom:1px solid #1e293b;
                       font-size:13px; color:#94a3b8; line-height:1.5;">
                {s['reason']}
            </td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="margin:0; padding:0; background:#0a0e17; font-family:'Segoe UI',Arial,sans-serif;">

      <div style="max-width:700px; margin:40px auto; background:#111827;
                  border:1px solid #1e3a5f; border-radius:16px; overflow:hidden;">

        <!-- Header -->
        <div style="background:linear-gradient(135deg,#0f172a,#1e293b);
                    padding:28px 32px; border-bottom:1px solid #1e3a5f;">
          <div style="font-family:'Courier New',monospace; font-size:20px;
                      font-weight:700; color:#38bdf8; letter-spacing:-0.02em;">
            📡 CRYPTO BOT MONITOR
          </div>
          <div style="font-size:13px; color:#64748b; margin-top:6px;">
            Signaux IA — Gemini 2.5 Flash Lite &nbsp;·&nbsp; {now}
          </div>
        </div>

        <!-- Tableau signaux -->
        <div style="padding:24px 32px;">
          <div style="font-size:13px; color:#64748b; text-transform:uppercase;
                      letter-spacing:0.08em; margin-bottom:16px;">
            {len(signals)} signal{"s" if len(signals) > 1 else ""} détecté{"s" if len(signals) > 1 else ""}
          </div>

          <table style="width:100%; border-collapse:collapse; background:#0f172a;
                        border:1px solid #1e293b; border-radius:12px; overflow:hidden;">
            <thead>
              <tr style="background:#1e293b;">
                <th style="padding:12px 20px; text-align:left; font-size:11px;
                           color:#475569; text-transform:uppercase; letter-spacing:0.08em;
                           font-family:'Courier New',monospace;">Token</th>
                <th style="padding:12px 20px; text-align:center; font-size:11px;
                           color:#475569; text-transform:uppercase; letter-spacing:0.08em;
                           font-family:'Courier New',monospace;">Signal</th>
                <th style="padding:12px 20px; text-align:center; font-size:11px;
                           color:#475569; text-transform:uppercase; letter-spacing:0.08em;
                           font-family:'Courier New',monospace;">Confiance</th>
                <th style="padding:12px 20px; text-align:left; font-size:11px;
                           color:#475569; text-transform:uppercase; letter-spacing:0.08em;
                           font-family:'Courier New',monospace;">Analyse</th>
              </tr>
            </thead>
            <tbody>
              {rows_html}
            </tbody>
          </table>
        </div>

        <!-- Footer -->
        <div style="padding:20px 32px; border-top:1px solid #1e293b;
                    font-size:11px; color:#334155; text-align:center;
                    font-family:'Courier New',monospace;">
          Les signaux sont indicatifs uniquement. Ne constitue pas un conseil financier.
        </div>

      </div>
    </body>
    </html>
    """

    return subject, html


def send_email(subject: str, html_body: str) -> bool:
    """
    Envoie l'email via Gmail SMTP.

    Returns:
        True si envoyé avec succès, False sinon
    """
    if not all([GMAIL_SENDER, GMAIL_PASSWORD, GMAIL_RECIPIENT]):
        logger.warning("Credentials Gmail manquants — email non envoyé.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"Crypto Bot <{GMAIL_SENDER}>"
        msg["To"]      = GMAIL_RECIPIENT

        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_SENDER, GMAIL_PASSWORD)
            server.sendmail(GMAIL_SENDER, GMAIL_RECIPIENT, msg.as_string())

        logger.info("Email envoye a %s : %s", GMAIL_RECIPIENT, subject)
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("Erreur d'authentification Gmail. Verifie GMAIL_SENDER et GMAIL_PASSWORD.")
        return False
    except smtplib.SMTPException as e:
        logger.error("Erreur SMTP : %s", e)
        return False
    except Exception as e:
        logger.error("Erreur inattendue lors de l'envoi : %s", e)
        return False


def check_and_alert():
    """
    Vérifie les derniers signaux et envoie une alerte si nécessaire.
    Appelé automatiquement après chaque analyse IA.
    """
    if not all([GMAIL_SENDER, GMAIL_PASSWORD, GMAIL_RECIPIENT]):
        logger.info("Alertes email non configurees — ignorees.")
        return

    # Récupérer les signaux de la dernière heure
    recent = get_recent_signals(limit=10)

    # Filtrer : seulement BUY/SELL avec confiance suffisante
    alerts = [
        s for s in recent
        if s["signal"] in ALERT_SIGNALS
        and s["confidence"] >= CONFIDENCE_THRESHOLD
    ]

    if not alerts:
        logger.info("Aucun signal fort detecte — pas d'email envoye.")
        return

    logger.info("%d signal(s) fort(s) detecte(s) → envoi email...", len(alerts))

    subject, html = build_email_html(alerts)
    success = send_email(subject, html)

    if success:
        logger.info("Alerte email envoyee avec succes.")
    else:
        logger.error("Echec de l'envoi de l'alerte email.")


if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    check_and_alert()
