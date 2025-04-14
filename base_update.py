import sqlite3
import json

class BaseUpdater:
    def __init__(self, conn):
        self.conn = conn
        self.cursor = conn.cursor()

    def insert_deal(self, rebalancing_id, date, manager_id, portfolio_id, actif_achete=None, actif_vendu=None):
        self.cursor.execute("""
            INSERT INTO Deals (rebalancing_id, date, manager_id, portefeuille_id, actif_achete, actif_vendu)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (rebalancing_id, date, manager_id, portfolio_id, actif_achete, actif_vendu))

    def insert_portfolio_snapshot(self, rebalancing_id, date, portfolio_id, manager_id, nom_portefeuille, produits, rendement_moyen):
        self.cursor.execute("""
            INSERT INTO Portefeuilles_suivi (rebalancing_id, date, portfolio_id, manager_id, nom_portefeuille, produits, rendement_moyen)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (rebalancing_id, date, portfolio_id, manager_id, nom_portefeuille, json.dumps(produits), rendement_moyen))

    def commit(self):
        self.conn.commit()
