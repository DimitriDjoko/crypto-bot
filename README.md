# 🤖 Crypto Trading Bot

Stack 100% gratuite — Python + Gemini AI + GitHub Actions + SQLite

## 🗂️ Structure du projet

```
crypto_bot/
├── config.py              # Configuration centralisée
├── fetch_prices.py         # Collecte des prix (Semaine 1) ✅
├── storage.py              # Base de données SQLite (Semaine 1) ✅
├── ai_analysis.py          # Analyse IA + signaux (Semaine 2) 🔜
├── alerts.py               # Email + Discord (Semaine 3) 🔜
├── dashboard.py            # Streamlit (Semaine 3) 🔜
├── requirements.txt
├── .env.example            # Template pour les clés API
└── .github/
    └── workflows/
        └── fetch_prices.yml  # Automatisation GitHub Actions
```

## 🚀 Démarrage rapide (Semaine 1)

### 1. Cloner et installer

```bash
git clone https://github.com/TON_USERNAME/crypto-bot.git
cd crypto-bot
pip install -r requirements.txt
```

### 2. Configurer les variables d'environnement

```bash
cp .env.example .env
# Éditer .env avec tes clés (pour l'instant, aucune clé nécessaire pour la Semaine 1)
```

### 3. Tester localement

```bash
python fetch_prices.py
```

Tu devrais voir un tableau des prix s'afficher et un fichier `crypto_data.db` créé.

### 4. Déployer sur GitHub Actions (exécution automatique gratuite)

1. Push le code sur GitHub
2. Aller dans **Settings → Secrets and variables → Actions**
3. Ajouter les secrets (GEMINI_API_KEY, DISCORD_WEBHOOK_URL, etc.) quand tu en auras besoin
4. Le workflow se déclenchera automatiquement toutes les heures

## 💰 Coût : $0/mois

| Service              | Alternative gratuite       |
|----------------------|---------------------------|
| Azure Functions $5   | GitHub Actions (gratuit)  |
| Azure CosmosDB $25   | SQLite / Supabase free    |
| Claude API $20       | Gemini Flash (gratuit)    |
| **Total**            | **$0**                    |

## 🗓️ Roadmap

- **Semaine 1** ✅ — Collecte des prix + SQLite
- **Semaine 2** 🔜 — Intégration Gemini AI + signaux BUY/SELL
- **Semaine 3** 🔜 — Alertes Discord + Dashboard Streamlit
- **Semaine 4** 🔜 — Optimisation + tests complets
