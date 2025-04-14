import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import json

class PerformanceAnalyzer:
    def __init__(self, db_path="Fund.db"):
        self.conn = sqlite3.connect(db_path)

    def load_performance_data(self):
        df = pd.read_sql_query("SELECT date, portfolio_id, nom_portefeuille, rendement_moyen FROM Portefeuilles_suivi", self.conn)
        df['date'] = pd.to_datetime(df['date'])
        return df.sort_values(['portfolio_id', 'date'])

    def compute_volatility_annualized(self, df):
        return df.groupby('nom_portefeuille')['rendement_moyen'].std() * (52 ** 0.5)

    def compute_cumulative_returns(self, df):
        df['rendement_moyen'] = pd.to_numeric(df['rendement_moyen'], errors='coerce')
        df['cumulative_return'] = df.groupby('portfolio_id')['rendement_moyen'].cumsum()
        return df

    def compute_sharpe_ratios(self, df, risk_free_rate=0.01):
        return df.groupby('nom_portefeuille')['rendement_moyen'].apply(
            lambda x: (x.mean() - risk_free_rate) / x.std() * (52 ** 0.5)
        )

    def compute_total_returns(self, df):
        return df.groupby('nom_portefeuille')['rendement_moyen'].sum()

    def compute_annualized_returns(self, df):
        annualized = {}
        grouped = df.groupby('nom_portefeuille')

        for name, group in grouped:
            group = group.sort_values('date')
            cumulative = group['rendement_moyen'].sum()
            n_years = (group['date'].max() - group['date'].min()).days / 365.25
            annualized_return = (1 + cumulative) ** (1 / n_years) - 1
            annualized[name] = annualized_return

        return pd.Series(annualized)

    def compute_best_manager(self):
        df = pd.read_sql_query("SELECT manager_id, nom_portefeuille, rendement_moyen FROM Portefeuilles_suivi", self.conn)
        return df.groupby('manager_id')['rendement_moyen'].mean().idxmax()

    def plot_performance_curves(self, df):
        df = df.copy()
        df['cumulative_return'] = df.groupby('portfolio_id')['rendement_moyen'].cumsum()
        plt.figure(figsize=(12, 6))
        
        for name, group in df.groupby('nom_portefeuille'):
            group_sorted = group.sort_values('date')
            plt.plot(group_sorted['date'], group_sorted['cumulative_return'], label=name)

        plt.legend()
        plt.title("Courbe de performance cumulative par portefeuille")
        plt.xlabel("Date")
        plt.ylabel("Rendement cumulé")
        plt.tight_layout()
        plt.show()

    def analyze(self):
        df = self.load_performance_data()
        df = self.compute_cumulative_returns(df)

        print("===== Performance des Portefeuilles (2020–2024) =====")

        total_returns = self.compute_total_returns(df)
        print("\n🎯 Rendement total :")
        for portefeuille, val in total_returns.items():
            print(f"{portefeuille} : {val:.2f}")

        ann_return = self.compute_annualized_returns(df)
        print("\n📅 Rendement annualisé :")
        for portefeuille, val in ann_return.items():
            print(f"{portefeuille} : {val*100:.2f}%")

        vol = self.compute_volatility_annualized(df)
        print("\n📉 Volatilité annualisée :")
        for portefeuille, val in vol.items():
            print(f"{portefeuille} : {val*100:.2f}%")

        sharpe = self.compute_sharpe_ratios(df)
        print("\n📈 Ratio de Sharpe :")
        for portefeuille, val in sharpe.items():
            print(f"{portefeuille} : {val:.4f}")

        best_manager = self.compute_best_manager()
        print(f"\n🏆 Manager le plus performant : Manager {best_manager}")

        print("\n📊 Courbe de performance")
        self.plot_performance_curves(df)

if __name__ == "__main__":
    analyzer = PerformanceAnalyzer()
    analyzer.analyze()
