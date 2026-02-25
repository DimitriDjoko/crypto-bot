"""
Script Complet pour Interroger une Base de Données
Supporte: SQL (MySQL, PostgreSQL, SQLite), MongoDB, Firebase, CSV

Usage:
    python query_database.py --type sql --query "SELECT * FROM users LIMIT 10"
    python query_database.py --type mongodb --collection users --find '{"age": {">": 25}}'
"""

import os
import sys
import json
import argparse
from typing import List, Dict, Any
from datetime import datetime
import csv
from pathlib import Path

# ===== IMPORTS OPTIONNELS (installer au besoin) =====
try:
    import sqlite3
except ImportError:
    print("⚠️ SQLite3 est inclus avec Python")

try:
    import mysql.connector
except ImportError:
    print("💡 Pour MySQL: pip install mysql-connector-python")

try:
    import psycopg2
except ImportError:
    print("💡 Pour PostgreSQL: pip install psycopg2-binary")

try:
    from pymongo import MongoClient
except ImportError:
    print("💡 Pour MongoDB: pip install pymongo")

try:
    import firebase_admin
    from firebase_admin import db, credentials
except ImportError:
    print("💡 Pour Firebase: pip install firebase-admin")

try:
    import pandas as pd
except ImportError:
    print("💡 Pour pandas (optionnel): pip install pandas")


# ===== 1. SQL DATABASE QUERIES =====

class SQLDatabase:
    """
    Classe pour interroger des bases de données SQL
    Supporte: SQLite, MySQL, PostgreSQL
    """
    
    def __init__(self, db_type: str, **kwargs):
        """
        Args:
            db_type: 'sqlite', 'mysql', 'postgresql'
            **kwargs: paramètres de connexion
        """
        self.db_type = db_type
        self.connection = None
        self.cursor = None
        self._connect(**kwargs)
    
    def _connect(self, **kwargs):
        """Établit la connexion à la base de données"""
        try:
            if self.db_type == 'sqlite':
                # SQLite (fichier local)
                db_path = kwargs.get('path', 'database.db')
                self.connection = sqlite3.connect(db_path)
                self.cursor = self.connection.cursor()
                print(f"✅ Connecté à SQLite: {db_path}")
            
            elif self.db_type == 'mysql':
                # MySQL
                self.connection = mysql.connector.connect(
                    host=kwargs.get('host', 'localhost'),
                    user=kwargs.get('user', 'root'),
                    password=kwargs.get('password', ''),
                    database=kwargs.get('database', 'mydb')
                )
                self.cursor = self.connection.cursor()
                print(f"✅ Connecté à MySQL: {kwargs.get('database')}")
            
            elif self.db_type == 'postgresql':
                # PostgreSQL
                self.connection = psycopg2.connect(
                    host=kwargs.get('host', 'localhost'),
                    user=kwargs.get('user', 'postgres'),
                    password=kwargs.get('password', ''),
                    database=kwargs.get('database', 'mydb')
                )
                self.cursor = self.connection.cursor()
                print(f"✅ Connecté à PostgreSQL: {kwargs.get('database')}")
            
            else:
                raise ValueError(f"Type DB non supporté: {self.db_type}")
        
        except Exception as e:
            print(f"❌ Erreur de connexion: {e}")
            sys.exit(1)
    
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Exécute une requête SELECT et retourne les résultats"""
        try:
            self.cursor.execute(query)
            
            # Récupérer les noms de colonnes
            columns = [desc[0] for desc in self.cursor.description]
            
            # Récupérer les données
            rows = self.cursor.fetchall()
            
            # Convertir en liste de dictionnaires
            results = [dict(zip(columns, row)) for row in rows]
            
            return results
        
        except Exception as e:
            print(f"❌ Erreur requête: {e}")
            return []
    
    def execute_insert(self, query: str, values: tuple = None):
        """Exécute une insertion (INSERT, UPDATE, DELETE)"""
        try:
            if values:
                self.cursor.execute(query, values)
            else:
                self.cursor.execute(query)
            
            self.connection.commit()
            print(f"✅ Exécution réussie ({self.cursor.rowcount} lignes affectées)")
            return True
        
        except Exception as e:
            print(f"❌ Erreur: {e}")
            self.connection.rollback()
            return False
    
    def get_tables(self) -> List[str]:
        """Récupère la liste des tables"""
        try:
            if self.db_type == 'sqlite':
                query = "SELECT name FROM sqlite_master WHERE type='table';"
            elif self.db_type == 'mysql':
                query = "SHOW TABLES;"
            elif self.db_type == 'postgresql':
                query = "SELECT table_name FROM information_schema.tables WHERE table_schema='public';"
            
            self.cursor.execute(query)
            tables = [row[0] for row in self.cursor.fetchall()]
            return tables
        
        except Exception as e:
            print(f"❌ Erreur: {e}")
            return []
    
    def get_schema(self, table: str) -> List[Dict[str, str]]:
        """Récupère le schéma d'une table"""
        try:
            if self.db_type == 'sqlite':
                self.cursor.execute(f"PRAGMA table_info({table});")
                columns = self.cursor.fetchall()
                return [
                    {'column': col[1], 'type': col[2], 'notnull': col[3], 'pk': col[5]}
                    for col in columns
                ]
            
            elif self.db_type == 'mysql':
                query = f"DESCRIBE {table};"
                self.cursor.execute(query)
                columns = self.cursor.fetchall()
                return [
                    {'column': col[0], 'type': col[1], 'null': col[2], 'key': col[3]}
                    for col in columns
                ]
            
            elif self.db_type == 'postgresql':
                query = f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name='{table}';
                """
                self.cursor.execute(query)
                columns = self.cursor.fetchall()
                return [{'column': col[0], 'type': col[1]} for col in columns]
        
        except Exception as e:
            print(f"❌ Erreur: {e}")
            return []
    
    def close(self):
        """Ferme la connexion"""
        if self.connection:
            self.connection.close()
            print("🔌 Connexion fermée")


# ===== 2. MONGODB QUERIES =====

class MongoDatabase:
    """Classe pour interroger MongoDB"""
    
    def __init__(self, uri: str = "mongodb://localhost:27017/", database: str = "mydb"):
        """
        Args:
            uri: Connexion string MongoDB
            database: Nom de la base de données
        """
        try:
            self.client = MongoClient(uri)
            self.db = self.client[database]
            print(f"✅ Connecté à MongoDB: {database}")
        except Exception as e:
            print(f"❌ Erreur de connexion MongoDB: {e}")
            sys.exit(1)
    
    def find(self, collection: str, query: Dict = None, limit: int = 10) -> List[Dict]:
        """
        Recherche des documents
        
        Args:
            collection: Nom de la collection
            query: Filtre MongoDB (ex: {"age": {">": 25}})
            limit: Nombre max de résultats
        """
        try:
            if query is None:
                query = {}
            
            results = list(
                self.db[collection].find(query).limit(limit)
            )
            
            # Convertir ObjectId en string pour JSON
            for doc in results:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
            
            return results
        
        except Exception as e:
            print(f"❌ Erreur requête: {e}")
            return []
    
    def insert(self, collection: str, document: Dict) -> bool:
        """Insère un document"""
        try:
            result = self.db[collection].insert_one(document)
            print(f"✅ Document inséré (ID: {result.inserted_id})")
            return True
        except Exception as e:
            print(f"❌ Erreur: {e}")
            return False
    
    def update(self, collection: str, query: Dict, update: Dict) -> int:
        """Met à jour des documents"""
        try:
            result = self.db[collection].update_many(query, {"$set": update})
            print(f"✅ {result.modified_count} documents mis à jour")
            return result.modified_count
        except Exception as e:
            print(f"❌ Erreur: {e}")
            return 0
    
    def delete(self, collection: str, query: Dict) -> int:
        """Supprime des documents"""
        try:
            result = self.db[collection].delete_many(query)
            print(f"✅ {result.deleted_count} documents supprimés")
            return result.deleted_count
        except Exception as e:
            print(f"❌ Erreur: {e}")
            return 0
    
    def get_collections(self) -> List[str]:
        """Récupère la liste des collections"""
        return self.db.list_collection_names()
    
    def count(self, collection: str, query: Dict = None) -> int:
        """Compte les documents"""
        if query is None:
            query = {}
        return self.db[collection].count_documents(query)
    
    def close(self):
        """Ferme la connexion"""
        self.client.close()
        print("🔌 Connexion fermée")


# ===== 3. CSV FILE QUERIES =====

class CSVDatabase:
    """Classe pour interroger des fichiers CSV"""
    
    def __init__(self, file_path: str):
        """
        Args:
            file_path: Chemin du fichier CSV
        """
        self.file_path = file_path
        self.data = []
        self._load_csv()
    
    def _load_csv(self):
        """Charge le fichier CSV"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.data = list(reader)
            print(f"✅ CSV chargé: {len(self.data)} lignes")
        except Exception as e:
            print(f"❌ Erreur: {e}")
    
    def filter(self, column: str, value: Any, operator: str = '==') -> List[Dict]:
        """Filtre les données"""
        results = []
        for row in self.data:
            row_value = row.get(column, '')
            
            # Conversion de type si possible
            try:
                if row_value.replace('.', '').isdigit():
                    row_value = float(row_value)
                    value = float(value)
            except:
                pass
            
            # Comparaison
            if operator == '==' and row_value == value:
                results.append(row)
            elif operator == '!=' and row_value != value:
                results.append(row)
            elif operator == '>' and row_value > value:
                results.append(row)
            elif operator == '<' and row_value < value:
                results.append(row)
            elif operator == 'contains' and str(value).lower() in str(row_value).lower():
                results.append(row)
        
        return results
    
    def search(self, keyword: str) -> List[Dict]:
        """Recherche un mot-clé dans tous les champs"""
        results = []
        for row in self.data:
            if any(keyword.lower() in str(v).lower() for v in row.values()):
                results.append(row)
        return results
    
    def get_columns(self) -> List[str]:
        """Récupère les noms de colonnes"""
        if self.data:
            return list(self.data[0].keys())
        return []
    
    def limit(self, n: int) -> List[Dict]:
        """Récupère les n premières lignes"""
        return self.data[:n]


# ===== 4. FIREBASE REALTIME DATABASE =====

class FirebaseDatabase:
    """Classe pour Firebase Realtime Database"""
    
    def __init__(self, credentials_path: str, database_url: str):
        """
        Args:
            credentials_path: Chemin du fichier JSON credentials
            database_url: URL de Firebase (ex: https://myproject.firebaseio.com)
        """
        try:
            cred = credentials.Certificate(credentials_path)
            firebase_admin.initialize_app(cred, {
                'databaseURL': database_url
            })
            print(f"✅ Connecté à Firebase")
        except Exception as e:
            print(f"❌ Erreur Firebase: {e}")
            sys.exit(1)
    
    def get(self, path: str) -> Dict:
        """Récupère les données à un chemin"""
        try:
            data = db.reference(path).get()
            return data if data else {}
        except Exception as e:
            print(f"❌ Erreur: {e}")
            return {}
    
    def set(self, path: str, data: Dict) -> bool:
        """Ajoute/remplace les données"""
        try:
            db.reference(path).set(data)
            print(f"✅ Données sauvegardées")
            return True
        except Exception as e:
            print(f"❌ Erreur: {e}")
            return False
    
    def update(self, path: str, data: Dict) -> bool:
        """Met à jour les données"""
        try:
            db.reference(path).update(data)
            print(f"✅ Données mises à jour")
            return True
        except Exception as e:
            print(f"❌ Erreur: {e}")
            return False
    
    def delete(self, path: str) -> bool:
        """Supprime les données"""
        try:
            db.reference(path).delete()
            print(f"✅ Données supprimées")
            return True
        except Exception as e:
            print(f"❌ Erreur: {e}")
            return False


# ===== 5. UTILITAIRES D'AFFICHAGE =====

def print_results(results: List[Dict], format: str = 'table', limit: int = None):
    """Affiche les résultats dans différents formats"""
    
    if not results:
        print("❌ Aucun résultat")
        return
    
    if limit:
        results = results[:limit]
    
    print(f"\n📊 {len(results)} résultat(s):\n")
    
    if format == 'json':
        print(json.dumps(results, indent=2, ensure_ascii=False))
    
    elif format == 'table':
        try:
            import pandas as pd
            df = pd.DataFrame(results)
            print(df.to_string(index=False))
        except ImportError:
            # Fallback sans pandas
            for i, row in enumerate(results, 1):
                print(f"\n{i}. {row}")
    
    elif format == 'csv':
        if results:
            writer = csv.DictWriter(sys.stdout, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
    
    else:  # format == 'pretty'
        for i, row in enumerate(results, 1):
            print(f"\n{'='*50}")
            print(f"Résultat {i}:")
            print('='*50)
            for key, value in row.items():
                print(f"  {key}: {value}")


def save_results(results: List[Dict], output_file: str):
    """Sauvegarde les résultats dans un fichier"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"✅ Résultats sauvegardés: {output_file}")
    except Exception as e:
        print(f"❌ Erreur: {e}")


# ===== 6. EXEMPLES D'UTILISATION =====

def examples():
    """Affiche des exemples d'utilisation"""
    
    examples_text = """
╔════════════════════════════════════════════════════════════════╗
║          EXEMPLES D'UTILISATION                                ║
╚════════════════════════════════════════════════════════════════╝

1️⃣  SQLite (Local)
────────────────────
db = SQLDatabase('sqlite', path='database.db')
results = db.execute_query('SELECT * FROM users LIMIT 10')
print_results(results)
db.close()

2️⃣  MySQL
─────────
db = SQLDatabase('mysql',
    host='localhost',
    user='root',
    password='password',
    database='mydb'
)
results = db.execute_query('SELECT * FROM products WHERE price > 100')
print_results(results)

3️⃣  PostgreSQL
──────────────
db = SQLDatabase('postgresql',
    host='localhost',
    user='postgres',
    password='password',
    database='mydb'
)
tables = db.get_tables()
schema = db.get_schema('users')
print(f"Tables: {tables}")
print(f"Schema: {schema}")

4️⃣  MongoDB
───────────
mongo = MongoDatabase(
    uri='mongodb://localhost:27017/',
    database='mydb'
)
# Trouver tous les documents
results = mongo.find('users')

# Avec filtre
results = mongo.find('users', {'age': {'>': 25}}, limit=20)

# Insérer
mongo.insert('users', {'name': 'John', 'age': 30})

# Mettre à jour
mongo.update('users', {'name': 'John'}, {'age': 31})

# Supprimer
mongo.delete('users', {'name': 'John'})

5️⃣  CSV File
────────────
csv_db = CSVDatabase('data.csv')

# Voir les colonnes
print(csv_db.get_columns())

# Filtrer
results = csv_db.filter('age', 30, operator='>')

# Rechercher
results = csv_db.search('John')

# Limiter
results = csv_db.limit(10)

6️⃣  Firebase
────────────
firebase = FirebaseDatabase(
    'path/to/credentials.json',
    'https://myproject.firebaseio.com'
)

# Récupérer
data = firebase.get('/users')

# Ajouter
firebase.set('/users/user1', {'name': 'John', 'age': 30})

# Mettre à jour
firebase.update('/users/user1', {'age': 31})

# Supprimer
firebase.delete('/users/user1')

════════════════════════════════════════════════════════════════
    """
    
    print(examples_text)


# ===== 7. CLI INTERFACE =====

def main():
    parser = argparse.ArgumentParser(
        description='🗄️  Script Complet pour Interroger une Base de Données',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
EXEMPLES:
  python query_database.py --type sqlite --path database.db --query "SELECT * FROM users LIMIT 10"
  python query_database.py --type mysql --host localhost --user root --password pass --database mydb --query "SELECT * FROM products"
  python query_database.py --type mongodb --uri "mongodb://localhost:27017/" --database mydb --collection users --find '{"age": {">": 25}}'
  python query_database.py --type csv --file data.csv --filter "age,30,>"
  python query_database.py --examples
        '''
    )
    
    parser.add_argument('--type', choices=['sqlite', 'mysql', 'postgresql', 'mongodb', 'csv', 'firebase'],
                       help='Type de base de données')
    parser.add_argument('--examples', action='store_true', help='Affiche les exemples')
    parser.add_argument('--query', help='Requête SQL')
    parser.add_argument('--path', help='Chemin (SQLite)')
    parser.add_argument('--host', default='localhost', help='Hôte (MySQL, PostgreSQL)')
    parser.add_argument('--user', help='Utilisateur (MySQL, PostgreSQL)')
    parser.add_argument('--password', help='Mot de passe (MySQL, PostgreSQL)')
    parser.add_argument('--database', help='Base de données')
    parser.add_argument('--uri', help='Connection string (MongoDB)')
    parser.add_argument('--collection', help='Collection (MongoDB)')
    parser.add_argument('--find', help='Filtre MongoDB (JSON)')
    parser.add_argument('--file', help='Fichier CSV')
    parser.add_argument('--filter', help='Filtre CSV (column,value,operator)')
    parser.add_argument('--search', help='Mot-clé à rechercher (CSV)')
    parser.add_argument('--format', choices=['json', 'table', 'csv', 'pretty'], default='table',
                       help='Format de sortie')
    parser.add_argument('--limit', type=int, help='Nombre max de résultats')
    parser.add_argument('--output', help='Fichier de sortie (JSON)')
    
    args = parser.parse_args()
    
    # Afficher les exemples
    if args.examples:
        examples()
        return
    
    # Requête SQLite
    if args.type == 'sqlite':
        if not args.query:
            print("❌ --query requis pour SQLite")
            return
        
        db = SQLDatabase('sqlite', path=args.path or 'database.db')
        results = db.execute_query(args.query)
        print_results(results, format=args.format, limit=args.limit)
        if args.output:
            save_results(results, args.output)
        db.close()
    
    # Requête MySQL
    elif args.type == 'mysql':
        if not args.query or not args.user:
            print("❌ --query et --user requis pour MySQL")
            return
        
        db = SQLDatabase('mysql',
            host=args.host,
            user=args.user,
            password=args.password or '',
            database=args.database or 'mydb'
        )
        results = db.execute_query(args.query)
        print_results(results, format=args.format, limit=args.limit)
        if args.output:
            save_results(results, args.output)
        db.close()
    
    # Requête PostgreSQL
    elif args.type == 'postgresql':
        if not args.query or not args.user:
            print("❌ --query et --user requis pour PostgreSQL")
            return
        
        db = SQLDatabase('postgresql',
            host=args.host,
            user=args.user,
            password=args.password or '',
            database=args.database or 'mydb'
        )
        results = db.execute_query(args.query)
        print_results(results, format=args.format, limit=args.limit)
        if args.output:
            save_results(results, args.output)
        db.close()
    
    # MongoDB
    elif args.type == 'mongodb':
        if not args.collection:
            print("❌ --collection requis pour MongoDB")
            return
        
        mongo = MongoDatabase(
            uri=args.uri or 'mongodb://localhost:27017/',
            database=args.database or 'mydb'
        )
        
        if args.find:
            query = json.loads(args.find)
            results = mongo.find(args.collection, query, limit=args.limit or 10)
        elif args.search:
            # Recherche simple
            results = mongo.find(args.collection, limit=args.limit or 10)
            results = [r for r in results if any(args.search.lower() in str(v).lower() for v in r.values())]
        else:
            results = mongo.find(args.collection, limit=args.limit or 10)
        
        print_results(results, format=args.format, limit=args.limit)
        if args.output:
            save_results(results, args.output)
        mongo.close()
    
    # CSV
    elif args.type == 'csv':
        if not args.file:
            print("❌ --file requis pour CSV")
            return
        
        csv_db = CSVDatabase(args.file)
        
        if args.filter:
            parts = args.filter.split(',')
            column, value, operator = parts[0], parts[1], parts[2] if len(parts) > 2 else '=='
            results = csv_db.filter(column, value, operator)
        elif args.search:
            results = csv_db.search(args.search)
        else:
            results = csv_db.limit(args.limit or 10)
        
        print_results(results, format=args.format, limit=args.limit)
        if args.output:
            save_results(results, args.output)
    
    else:
        print("❌ Veuillez spécifier un type avec --type")
        parser.print_help()


if __name__ == '__main__':
    main()
