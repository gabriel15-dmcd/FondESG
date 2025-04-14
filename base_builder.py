import os
import json
import sqlite3
import datetime
import pandas as pd
from faker import Faker
from Data.full_dict import full_dict, full_sectors_dict

class FundDatabaseBuilder:
    def __init__(self, db_file="Fund.db", returns_file="Data/data_filtered.csv", actif_base_file="Data/actifs_base.csv"):
        self.db_file = db_file
        self.returns_file = returns_file
        self.actif_base_file = actif_base_file
        self.fake = Faker()
        self.returns_data = pd.read_csv(self.returns_file, index_col=0, parse_dates=True)
        self.actifs_base = pd.read_csv(self.actif_base_file)

    def generate_clients_data(self):
        clients = []
        end_date = datetime.datetime(2019, 12, 31)
        start_date = end_date - datetime.timedelta(days=8 * 365)
        portfolios = ["Green Growth Leader", "Stability", "ESG Global"]
        for portefeuille in portfolios:
            nom = self.fake.last_name().capitalize()
            prenom = self.fake.first_name().capitalize()
            naissance = self.fake.date_of_birth(minimum_age=18, maximum_age=80).strftime('%Y-%m-%d')
            adresse = self.fake.address().replace("\n", ", ")
            tel = self.fake.phone_number()
            email = f"{prenom.lower()}.{nom.lower()}@example.com"
            inscription = self.fake.date_between(start_date=start_date, end_date=end_date).strftime('%Y-%m-%d')
            clients.append((nom, prenom, naissance, adresse, tel, email, inscription, portefeuille))
        return clients

    def build_database(self):
        # Supprimer l'ancien fichier si nécessaire
        if os.path.exists(self.db_file):
            os.remove(self.db_file)
            print(f"Ancien fichier '{self.db_file}' supprimé.")

        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()

            # Créer la table Clients
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Clients (
                    client_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nom TEXT, prenom TEXT, date_naissance DATE,
                    adresse TEXT, telephone TEXT, email TEXT, date_inscription DATE,
                    nom_portefeuille TEXT
                );
            """)
            cursor.executemany("""
                INSERT INTO Clients (nom, prenom, date_naissance, adresse, telephone, email, date_inscription, nom_portefeuille)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, self.generate_clients_data())
            print("Table 'Clients' créée et remplie.")

            # Créer la table Portfolios
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Portfolios (
                    portfolio_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER,
                    nom_portefeuille TEXT,
                    date_creation DATE,
                    range_products TEXT,
                    FOREIGN KEY (client_id) REFERENCES Clients(client_id)
                );
            """)
            print("Table 'Portfolios' créée.")

            # Créer la table Products
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Products (
                    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT UNIQUE,
                    actif TEXT,
                    secteur TEXT,
                    rendement_moyen REAL,
                    volatilite_annualisee REAL,
                    score_environment REAL,
                    score_social REAL,
                    score_governance REAL,
                    score_total REAL
                );
            """)
            # Récupérer les données depuis le fichier actif_base
            actifs_base_dict = self.actifs_base.set_index("ticker").to_dict("index")
            products_data = [
                (ticker, full_dict[ticker],
                 actifs_base_dict[ticker]["secteur"], actifs_base_dict[ticker]["rendement_moyen"], 
                 actifs_base_dict[ticker]["volatilite_annualisee"], 
                 actifs_base_dict[ticker]["score_environment"], actifs_base_dict[ticker]["score_social"],
                 actifs_base_dict[ticker]["score_governance"], actifs_base_dict[ticker]["score_total"])
                for ticker in full_dict if ticker in actifs_base_dict
            ]
            cursor.executemany("""
                INSERT INTO Products (ticker, actif, secteur, rendement_moyen, volatilite_annualisee, 
                                      score_environment, score_social, score_governance, score_total)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, products_data)
            print("Table 'Products' créée et remplie.")

            # Créer la table Returns
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Returns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER,
                    ticker TEXT,
                    secteur TEXT,
                    date TEXT,
                    return_value REAL,
                    volatility_value REAL,
                    FOREIGN KEY (product_id) REFERENCES Products(product_id)
                );
            """)

            cursor.execute("SELECT product_id, ticker, secteur FROM Products")
            product_map = {ticker: (pid, secteur) for pid, ticker, secteur in cursor.fetchall()}
            returns_insert = [
                (product_map[row['id']][0], row['id'], product_map[row['id']][1], date.strftime('%Y-%m-%d'), row['return'], row['volatilite_journaliere'])
                for date, row in self.returns_data.iterrows() if row['id'] in product_map
            ]
            cursor.executemany("""
                INSERT INTO Returns (product_id, ticker, secteur, date, return_value, volatility_value)
                VALUES (?, ?, ?, ?, ?, ?);
            """, returns_insert)
            print("Table 'Returns' créée et remplie.")

            # Créer la table Managers
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Managers (
                    manager_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nom TEXT, prenom TEXT, adresse TEXT,
                    telephone TEXT, email TEXT, portefeuille TEXT
                );
            """)
            managers_data = []
            portfolios = ["Green Growth Leader", "Stability", "ESG Global"]
            for portefeuille in portfolios:
                nom = self.fake.last_name()
                prenom = self.fake.first_name()
                adresse = self.fake.address().replace("\n", ", ")
                tel = self.fake.phone_number()
                email = f"{prenom.lower()}.{nom.lower()}@fund.com"
                managers_data.append((nom, prenom, adresse, tel, email, portefeuille))
            cursor.executemany("""
                INSERT INTO Managers (nom, prenom, adresse, telephone, email, portefeuille)
                VALUES (?, ?, ?, ?, ?, ?);
            """, managers_data)
            print("Table 'Managers' créée et remplie.")

            # Créer la table Deals
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Deals (
                    rebalancing_id INTEGER,
                    date TEXT,
                    manager_id INTEGER,
                    portefeuille_id INTEGER,
                    actif_achete TEXT,
                    actif_vendu TEXT,
                    FOREIGN KEY (manager_id) REFERENCES Managers(manager_id),
                    FOREIGN KEY (portefeuille_id) REFERENCES Portfolios(portfolio_id),
                    FOREIGN KEY (rebalancing_id) REFERENCES Portefeuilles_suivi(rebalancing_id)
                );
            """)
            print("Table 'Deals' créée.")

            # Créer la table Portefeuilles_suivi
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Portefeuilles_suivi (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rebalancing_id INTEGER,
                    date TEXT,
                    portfolio_id INTEGER,
                    manager_id INTEGER,
                    nom_portefeuille TEXT,
                    produits TEXT,
                    rendement_moyen REAL,
                    FOREIGN KEY (portfolio_id) REFERENCES Portfolios(portfolio_id),
                    FOREIGN KEY (manager_id) REFERENCES Managers(manager_id)
                );
            """)
            print("Table 'Portefeuilles_suivi' créée.")

    def build_base(self, cursor):
        # Récupère les clients
        cursor.execute("SELECT client_id, nom_portefeuille FROM Clients")
        clients = cursor.fetchall()
        portfolio_data = []

        # Crée les portefeuilles
        for client_id, portfolio_type in clients:
            date_creation = "2020-01-02"
            portfolio_data.append((client_id, portfolio_type, date_creation))

        cursor.executemany("""
            INSERT INTO Portfolios (client_id, nom_portefeuille, date_creation)
            VALUES (?, ?, ?);
        """, portfolio_data)

if __name__ == "__main__":
    builder = FundDatabaseBuilder()
    builder.build_database()
    
    with sqlite3.connect(builder.db_file) as conn:
        cursor = conn.cursor()
        builder.build_base(cursor)
        conn.commit()
