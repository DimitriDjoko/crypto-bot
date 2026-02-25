"""
Script de Test pour query_database.py
Crée une BD de test et montre comment l'utiliser
"""

import sqlite3
import json
from pathlib import Path

# ===== 1. CRÉER UNE BASE DE DONNÉES DE TEST =====

def create_test_database():
    """Crée une base de données SQLite de test"""
    
    # Créer la connexion
    conn = sqlite3.connect('test_database.db')
    cursor = conn.cursor()
    
    print("📝 Création de la base de données de test...")
    
    # Créer la table users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            age INTEGER,
            city TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            active INTEGER DEFAULT 1
        )
    ''')
    
    # Créer la table products
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            price REAL,
            stock INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Créer la table orders
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            total_amount REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    ''')
    
    print("✅ Tables créées")
    
    # ===== 2. INSÉRER DES DONNÉES DE TEST =====
    
    print("\n📊 Insertion de données de test...")
    
    # Données utilisateurs
    users_data = [
        ('John Doe', 'john@example.com', 30, 'Paris', 1),
        ('Alice Smith', 'alice@example.com', 28, 'Lyon', 1),
        ('Bob Johnson', 'bob@example.com', 35, 'Marseille', 1),
        ('Carol White', 'carol@example.com', 26, 'Paris', 1),
        ('David Brown', 'david@example.com', 32, 'Toulouse', 0),
        ('Emma Davis', 'emma@example.com', 29, 'Nice', 1),
        ('Frank Miller', 'frank@example.com', 45, 'Paris', 1),
        ('Grace Wilson', 'grace@example.com', 24, 'Bordeaux', 1),
    ]
    
    cursor.executemany(
        'INSERT INTO users (name, email, age, city, active) VALUES (?, ?, ?, ?, ?)',
        users_data
    )
    
    # Données produits
    products_data = [
        ('Laptop', 'Electronics', 999.99, 50),
        ('Mouse', 'Electronics', 29.99, 200),
        ('Keyboard', 'Electronics', 79.99, 150),
        ('Monitor', 'Electronics', 299.99, 80),
        ('Desk Lamp', 'Furniture', 49.99, 120),
        ('Office Chair', 'Furniture', 199.99, 40),
        ('Coffee Maker', 'Kitchen', 89.99, 60),
        ('Bluetooth Speaker', 'Electronics', 59.99, 100),
    ]
    
    cursor.executemany(
        'INSERT INTO products (name, category, price, stock) VALUES (?, ?, ?, ?)',
        products_data
    )
    
    # Données commandes
    orders_data = [
        (1, 1, 1, 999.99),      # John commande 1 laptop
        (1, 2, 2, 59.98),       # John commande 2 souris
        (2, 3, 1, 79.99),       # Alice commande 1 clavier
        (2, 4, 1, 299.99),      # Alice commande 1 moniteur
        (3, 1, 1, 999.99),      # Bob commande 1 laptop
        (4, 5, 1, 49.99),       # Carol commande 1 lampe
        (5, 6, 1, 199.99),      # David commande 1 chaise
        (6, 7, 1, 89.99),       # Emma commande 1 cafetière
        (7, 2, 3, 89.97),       # Frank commande 3 souris
        (8, 8, 1, 59.99),       # Grace commande 1 speaker
    ]
    
    cursor.executemany(
        'INSERT INTO orders (user_id, product_id, quantity, total_amount) VALUES (?, ?, ?, ?)',
        orders_data
    )
    
    conn.commit()
    print(f"✅ {len(users_data)} utilisateurs insérés")
    print(f"✅ {len(products_data)} produits insérés")
    print(f"✅ {len(orders_data)} commandes insérées")
    
    conn.close()
    print("\n✅ Base de données créée: test_database.db")


# ===== 3. EXEMPLES D'UTILISATION =====

def run_examples():
    """Lance des exemples d'utilisation"""
    
    from query_database import SQLDatabase, print_results
    
    print("\n" + "="*60)
    print("🧪 EXEMPLES D'UTILISATION")
    print("="*60)
    
    # Connexion
    db = SQLDatabase('sqlite', path='test_database.db')
    
    # Exemple 1: Voir les tables
    print("\n1️⃣ Lister les tables")
    print("-" * 60)
    tables = db.get_tables()
    print(f"Tables dans la BD: {tables}")
    
    # Exemple 2: Voir le schéma
    print("\n2️⃣ Schéma de la table 'users'")
    print("-" * 60)
    schema = db.get_schema('users')
    print(f"{'Colonne':<20} {'Type':<15} {'PK':<5}")
    for col in schema:
        print(f"{col['column']:<20} {col['type']:<15} {col['pk']:<5}")
    
    # Exemple 3: Requête simple
    print("\n3️⃣ Sélectionner tous les utilisateurs")
    print("-" * 60)
    results = db.execute_query('SELECT * FROM users')
    print_results(results, format='table')
    
    # Exemple 4: Requête avec WHERE
    print("\n4️⃣ Utilisateurs de plus de 30 ans à Paris")
    print("-" * 60)
    results = db.execute_query('''
        SELECT name, email, age, city FROM users 
        WHERE age > 30 AND city = 'Paris'
    ''')
    print_results(results, format='table')
    
    # Exemple 5: Requête avec COUNT
    print("\n5️⃣ Nombre d'utilisateurs par ville")
    print("-" * 60)
    results = db.execute_query('''
        SELECT city, COUNT(*) as total 
        FROM users 
        GROUP BY city 
        ORDER BY total DESC
    ''')
    print_results(results, format='table')
    
    # Exemple 6: JOIN
    print("\n6️⃣ Commandes avec détails utilisateurs")
    print("-" * 60)
    results = db.execute_query('''
        SELECT 
            u.name,
            p.name as product,
            o.quantity,
            o.total_amount
        FROM orders o
        JOIN users u ON o.user_id = u.id
        JOIN products p ON o.product_id = p.id
        ORDER BY o.created_at DESC
    ''')
    print_results(results, format='table')
    
    # Exemple 7: Agrégation
    print("\n7️⃣ Statistiques par catégorie de produit")
    print("-" * 60)
    results = db.execute_query('''
        SELECT 
            category,
            COUNT(*) as total_products,
            AVG(price) as avg_price,
            MAX(price) as max_price,
            MIN(price) as min_price
        FROM products
        GROUP BY category
        ORDER BY avg_price DESC
    ''')
    print_results(results, format='table')
    
    # Exemple 8: Sous-requête
    print("\n8️⃣ Utilisateurs ayant dépensé plus de 500€")
    print("-" * 60)
    results = db.execute_query('''
        SELECT DISTINCT u.name, u.email
        FROM users u
        WHERE u.id IN (
            SELECT user_id FROM orders 
            WHERE total_amount > 500
        )
        ORDER BY u.name
    ''')
    print_results(results, format='table')
    
    # Exemple 9: TOP utilisateurs
    print("\n9️⃣ Top 3 utilisateurs par montant dépensé")
    print("-" * 60)
    results = db.execute_query('''
        SELECT 
            u.name,
            COUNT(o.id) as total_orders,
            SUM(o.total_amount) as total_spent
        FROM users u
        LEFT JOIN orders o ON u.id = o.user_id
        WHERE u.active = 1
        GROUP BY u.id, u.name
        ORDER BY total_spent DESC
        LIMIT 3
    ''')
    print_results(results, format='table')
    
    # Exemple 10: Export JSON
    print("\n🔟 Export en JSON")
    print("-" * 60)
    results = db.execute_query('SELECT * FROM users WHERE active = 1 LIMIT 3')
    with open('users_export.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("✅ Fichier créé: users_export.json")
    
    db.close()


# ===== 4. MENU INTERACTIF =====

def interactive_menu():
    """Menu interactif pour requêtes personnalisées"""
    
    from query_database import SQLDatabase, print_results
    
    db = SQLDatabase('sqlite', path='test_database.db')
    
    print("\n" + "="*60)
    print("💬 MENU INTERACTIF")
    print("="*60)
    
    while True:
        print("\nOptions:")
        print("1. Lister les tables")
        print("2. Voir le schéma d'une table")
        print("3. Exécuter une requête personnalisée")
        print("4. Quitter")
        
        choice = input("\nVotre choix (1-4): ").strip()
        
        if choice == '1':
            tables = db.get_tables()
            print(f"\nTables: {', '.join(tables)}")
        
        elif choice == '2':
            table = input("Nom de la table: ").strip()
            schema = db.get_schema(table)
            print(f"\nSchéma de '{table}':")
            for col in schema:
                print(f"  {col['column']:<20} {col['type']}")
        
        elif choice == '3':
            query = input("\nEntrez votre requête SQL:\n").strip()
            results = db.execute_query(query)
            print_results(results, format='table')
        
        elif choice == '4':
            print("Au revoir! 👋")
            break
        
        else:
            print("❌ Choix invalide")
    
    db.close()


# ===== 5. MAIN =====

if __name__ == '__main__':
    import sys
    
    print("🚀 Script de Test - query_database.py\n")
    
    # Créer la BD si elle n'existe pas
    if not Path('test_database.db').exists():
        create_test_database()
    else:
        print("✅ Base de données de test trouvée")
    
    # Menu
    print("\nQue voulez-vous faire?")
    print("1. Exécuter les exemples")
    print("2. Menu interactif")
    print("3. Quitter")
    
    choice = input("\nVotre choix (1-3): ").strip()
    
    if choice == '1':
        run_examples()
        print("\n✅ Exemples exécutés!")
    
    elif choice == '2':
        interactive_menu()
    
    elif choice == '3':
        print("Au revoir! 👋")
    
    else:
        print("❌ Choix invalide")
