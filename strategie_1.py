import sqlite3
import json

class PreSelectorESG:
    def __init__(self, db_path="Fund.db"):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()

    def get_all_products(self):
        self.cursor.execute("""
            SELECT product_id, score_environment, score_social, score_governance, score_total
            FROM Products
        """)
        rows = self.cursor.fetchall()
        return [
            {
                "product_id": row[0],
                "score_environment": row[1],
                "score_social": row[2],
                "score_governance": row[3],
                "score_total": row[4],
            }
            for row in rows
        ]

    def filter_by_portfolio(self, products, portfolio_name):
        if portfolio_name == "Green Growth Leader":
            return [p["product_id"] for p in products if p["score_environment"] is not None and p["score_environment"] < 2]
        elif portfolio_name == "Stability":
            return [p["product_id"] for p in products if (
                p["score_social"] is not None and p["score_social"] < 8 and
                p["score_governance"] is not None and p["score_governance"] < 5
            )]
        elif portfolio_name == "ESG Global":
            return [p["product_id"] for p in products if p["score_total"] is not None and p["score_total"] < 17]
        else:
            return []

    def update_range_products(self):
        products = self.get_all_products()

        self.cursor.execute("SELECT portfolio_id, nom_portefeuille FROM Portfolios")
        portfolios = self.cursor.fetchall()

        for portfolio_id, portfolio_name in portfolios:
            filtered_ids = self.filter_by_portfolio(products, portfolio_name)
            range_json = json.dumps(filtered_ids)

            self.cursor.execute("""
                UPDATE Portfolios
                SET range_products = ?
                WHERE portfolio_id = ?
            """, (range_json, portfolio_id))

            print(f"🔍 Portefeuille '{portfolio_name}' → {len(filtered_ids)} actifs retenus.")

        self.conn.commit()
        print("✅ Mise à jour terminée.")

if __name__ == "__main__":
    selector = PreSelectorESG()
    selector.update_range_products()
