# 🚀 Quick Start Guide - query_database.py

## 5 Minutes pour Commencer

### 1️⃣ Installation (30 secondes)

```bash
# Télécharger les scripts
# query_database.py (principal)
# test_query_database.py (exemples)

# Installer les dépendances optionnelles (au besoin)
pip install pandas
```

### 2️⃣ Créer une BD de test (1 minute)

```bash
python test_query_database.py
# Choisir option 1 pour créer la BD de test
```

Cela crée `test_database.db` avec:
- 📊 Table `users` (8 utilisateurs)
- 📦 Table `products` (8 produits)
- 🛒 Table `orders` (10 commandes)

### 3️⃣ Exécuter votre première requête (1 minute)

```bash
# Option A: Ligne de commande
python query_database.py --type sqlite --path test_database.db --query "SELECT * FROM users LIMIT 3"

# Option B: Python
python
>>> from query_database import SQLDatabase
>>> db = SQLDatabase('sqlite', path='test_database.db')
>>> results = db.execute_query('SELECT * FROM users LIMIT 3')
>>> for r in results: print(r)
```

Output:
```
{'id': 1, 'name': 'John Doe', 'email': 'john@example.com', 'age': 30, 'city': 'Paris', ...}
{'id': 2, 'name': 'Alice Smith', 'email': 'alice@example.com', 'age': 28, 'city': 'Lyon', ...}
{'id': 3, 'name': 'Bob Johnson', 'email': 'bob@example.com', 'age': 35, 'city': 'Marseille', ...}
```

### 4️⃣ Essayer les différents formats (2 minutes)

```bash
# Format Table (défaut - joli pour terminal)
python query_database.py --type sqlite --path test_database.db \
  --query "SELECT name, age, city FROM users LIMIT 5" --format table

# Format JSON (pour traitement)
python query_database.py --type sqlite --path test_database.db \
  --query "SELECT name, age, city FROM users LIMIT 5" --format json

# Format CSV (pour Excel)
python query_database.py --type sqlite --path test_database.db \
  --query "SELECT name, age, city FROM users LIMIT 5" --format csv

# Format Pretty (lisible)
python query_database.py --type sqlite --path test_database.db \
  --query "SELECT name, age, city FROM users LIMIT 5" --format pretty
```

---

## 📚 Cas d'Usage Courants

### Cas 1: Voir tous les utilisateurs

```bash
python query_database.py --type sqlite --path test_database.db \
  --query "SELECT * FROM users"
```

### Cas 2: Filtrer les utilisateurs (âge > 30)

```bash
python query_database.py --type sqlite --path test_database.db \
  --query "SELECT name, age FROM users WHERE age > 30"
```

### Cas 3: Compter par ville

```bash
python query_database.py --type sqlite --path test_database.db \
  --query "SELECT city, COUNT(*) as total FROM users GROUP BY city"
```

### Cas 4: Voir les commandes avec détails

```bash
python query_database.py --type sqlite --path test_database.db \
  --query "SELECT u.name, p.name, o.quantity, o.total_amount FROM orders o 
           JOIN users u ON o.user_id = u.id 
           JOIN products p ON o.product_id = p.id"
```

### Cas 5: Sauvegarder en JSON

```bash
python query_database.py --type sqlite --path test_database.db \
  --query "SELECT * FROM users" --format json --output users.json
```

---

## 🔌 Passer de SQLite à MySQL

### Étape 1: Installer MySQL

```bash
pip install mysql-connector-python
```

### Étape 2: Créer la base de données

```sql
CREATE DATABASE mydb;
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100),
    email VARCHAR(100),
    age INT
);
INSERT INTO users VALUES (1, 'John', 'john@example.com', 30);
```

### Étape 3: Interroger avec le script

```bash
python query_database.py --type mysql \
  --host localhost \
  --user root \
  --password yourpassword \
  --database mydb \
  --query "SELECT * FROM users"
```

---

## 💻 Utiliser en Python

### Connexion et Requête Simple

```python
from query_database import SQLDatabase, print_results

# Connexion
db = SQLDatabase('sqlite', path='test_database.db')

# Requête
results = db.execute_query('SELECT * FROM users LIMIT 5')

# Affichage
print_results(results, format='table')

# Fermeture
db.close()
```

### Traiter les Résultats

```python
from query_database import SQLDatabase

db = SQLDatabase('sqlite', path='test_database.db')
results = db.execute_query('SELECT * FROM users')

# Chaque résultat est un dictionnaire
for user in results:
    print(f"{user['name']}: {user['age']} ans, {user['city']}")

# Filtrer dans Python
over_30 = [u for u in results if u['age'] > 30]
print(f"Utilisateurs > 30: {len(over_30)}")

db.close()
```

### Affichage Personnalisé

```python
from query_database import SQLDatabase

db = SQLDatabase('sqlite', path='test_database.db')
results = db.execute_query('SELECT city, COUNT(*) as total FROM users GROUP BY city')

# Affichage personnalisé
print("VILLES | UTILISATEURS")
print("-" * 30)
for row in results:
    print(f"{row['city']:20} | {row['total']}")

db.close()
```

---

## 🔒 Travail avec Variables d'Environnement

### 1. Créer un fichier `.env`

```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=mypassword
DB_NAME=mydb
```

### 2. Utiliser dans Python

```python
from dotenv import load_dotenv
import os
from query_database import SQLDatabase

load_dotenv()  # Charge les variables du .env

db = SQLDatabase('mysql',
    host=os.getenv('DB_HOST'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_NAME')
)

results = db.execute_query('SELECT * FROM users')
```

---

## 📊 Sauvegarder les Résultats

### Exporter en JSON

```bash
python query_database.py --type sqlite --path test_database.db \
  --query "SELECT * FROM users" \
  --output users.json \
  --format json
```

### Exporter en CSV

```bash
python query_database.py --type sqlite --path test_database.db \
  --query "SELECT name, email, age FROM users" \
  --output users.csv \
  --format csv
```

### Exporter en Python

```python
from query_database import SQLDatabase, save_results

db = SQLDatabase('sqlite', path='test_database.db')
results = db.execute_query('SELECT * FROM users')

# Sauvegarder en JSON
save_results(results, 'users.json')

db.close()
```

---

## 🆘 Problèmes Courants

### "ModuleNotFoundError"

```bash
# Solution: Installer la dépendance
pip install mysql-connector-python  # pour MySQL
pip install pymongo  # pour MongoDB
pip install firebase-admin  # pour Firebase
```

### "Connection refused"

```
Erreur: Connection refused
Cause: La BD n'est pas lancée
Solution: Démarrer MySQL/PostgreSQL/MongoDB
```

```bash
# Mac/Linux
brew services start mysql

# Windows (cmd admin)
net start MySQL80
```

### "Access denied for user"

```
Erreur: Access denied for user 'root'@'localhost'
Cause: Mauvais mot de passe
Solution: Vérifier user/password dans la commande
```

### "No such table"

```
Erreur: no such table: users
Cause: La table n'existe pas
Solution: Voir les tables avec db.get_tables()
```

---

## 🎓 Prochaines Étapes

### 1. Maîtriser les Requêtes SQL

Ressources:
- [SQL Tutorial](https://www.sqlitetutor.com/)
- [W3Schools SQL](https://www.w3schools.com/sql/)

Pratique:
```bash
# Requêtes progressives
python query_database.py --type sqlite --path test_database.db \
  --query "SELECT * FROM users"  # Simple

python query_database.py --type sqlite --path test_database.db \
  --query "SELECT * FROM users WHERE age > 25"  # Avec filtre

python query_database.py --type sqlite --path test_database.db \
  --query "SELECT city, COUNT(*) FROM users GROUP BY city"  # Avec agrégation

python query_database.py --type sqlite --path test_database.db \
  --query "SELECT u.name, o.total_amount FROM users u JOIN orders o ON u.id = o.user_id"  # Avec JOIN
```

### 2. Passer à une Vraie BD

Migrez de SQLite à:
- MySQL (pour production simple)
- PostgreSQL (pour données complexes)
- MongoDB (pour données non-structurées)

### 3. Automatiser

Créer des scripts qui tournent régulièrement:

```python
import schedule
import time
from query_database import SQLDatabase

def daily_report():
    db = SQLDatabase('sqlite', path='test_database.db')
    results = db.execute_query('SELECT COUNT(*) as total FROM users')
    print(f"Total users today: {results[0]['total']}")
    db.close()

schedule.every().day.at("10:30").do(daily_report)

while True:
    schedule.run_pending()
    time.sleep(60)
```

---

## 🎯 Conseils Importants

✅ **À Faire**
- Utiliser `LIMIT` sur les grandes tables
- Sauvegarder les mots de passe en `.env`
- Tester les requêtes d'abord
- Commenter vos requêtes complexes

❌ **À Éviter**
- Hardcoder les mots de passe
- `SELECT *` sur tables énormes
- Requêtes sans `LIMIT`
- Confiance aveugle aux résultats

---

## 📞 Besoin d'Aide?

1. Voir `README_query_database.md` (documentation complète)
2. Voir `EXAMPLES_config.md` (configurations avancées)
3. Exécuter `python test_query_database.py` (exemples)
4. Utiliser `python query_database.py --examples` (affiche les exemples)

---

## 🚀 Vous Êtes Prêt!

```bash
# Lancez-vous!
python query_database.py --examples
python test_query_database.py
```

Bon courage! 💪
