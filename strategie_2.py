import sqlite3
import json
import pandas as pd
from datetime import datetime, timedelta
from base_update import BaseUpdater

class StrategyEngine:
    def __init__(self, db_path="Fund.db", top_n=10):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.updater = BaseUpdater(self.conn)
        self.top_n = top_n
        self.product_id_to_ticker = self._load_product_map()
        self.ticker_to_product_id = {v: k for k, v in self.product_id_to_ticker.items()}

    def _load_product_map(self):
        self.cursor.execute("SELECT product_id, ticker FROM Products")
        return {pid: ticker for pid, ticker in self.cursor.fetchall()}

    def get_range_product_ids(self, portfolio_id):
        self.cursor.execute("SELECT range_products FROM Portfolios WHERE portfolio_id = ?", (portfolio_id,))
        result = self.cursor.fetchone()
        if result and result[0]:
            try:
                return json.loads(result[0])
            except json.JSONDecodeError:
                return []
        return []

    def get_last_30d_returns(self, product_ids, reference_date):
        tickers = [self.product_id_to_ticker[pid] for pid in product_ids if pid in self.product_id_to_ticker]
        if not tickers:
            return pd.DataFrame()

        date_end = reference_date
        date_start = reference_date - timedelta(days=30)

        query = f"""
        SELECT date, ticker, return_value
        FROM Returns
        WHERE ticker IN ({','.join(['?'] * len(tickers))})
        AND date BETWEEN ? AND ?
        """
        df = pd.read_sql_query(query, self.conn, params=tickers + [date_start.strftime("%Y-%m-%d"), date_end.strftime("%Y-%m-%d")])
        df["date"] = pd.to_datetime(df["date"])
        return df

    def select_top_assets_with_moving_average(self, df_returns):
        if df_returns.empty:
            return []

        df = df_returns.copy()

        def calc_momentum(sub_df):
            sub_df = sub_df.sort_values("date").copy()
            sub_df["ma_30"] = sub_df["return_value"].rolling(window=30, min_periods=10).mean()
            sub_df["recent_mean"] = sub_df["return_value"].rolling(window=7, min_periods=3).mean()
            sub_df["ticker"] = sub_df["ticker"].iloc[0]
            return sub_df

        df_list = []
        for ticker, sub_df in df.groupby("ticker"):
            df_list.append(calc_momentum(sub_df))

        df = pd.concat(df_list).reset_index(drop=True)

        last_rows = df.groupby("ticker").tail(1)
        df_positive = last_rows[last_rows["recent_mean"] > last_rows["ma_30"]]
        top_positive = df_positive.sort_values("recent_mean", ascending=False)["ticker"].tolist()

        if len(top_positive) < self.top_n:
            remaining = last_rows[~last_rows["ticker"].isin(top_positive)]
            fallback = remaining.sort_values("recent_mean", ascending=False)["ticker"].tolist()
            top_positive += fallback[:self.top_n - len(top_positive)]

        return top_positive[:self.top_n]

    def get_current_assets(self, portfolio_id, reference_date):
        self.cursor.execute("""
            SELECT produits FROM Portefeuilles_suivi
            WHERE portfolio_id = ?
            AND date = (
                SELECT MAX(date) FROM Portefeuilles_suivi
                WHERE portfolio_id = ? AND date <= ?
            )
        """, (portfolio_id, portfolio_id, reference_date.strftime("%Y-%m-%d")))
        result = self.cursor.fetchone()
        if result and result[0]:
            try:
                return json.loads(result[0])
            except json.JSONDecodeError:
                return []
        return []

    def get_manager_id(self, portfolio_type):
        self.cursor.execute("SELECT manager_id FROM Managers WHERE portefeuille = ?", (portfolio_type,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def compute_mean_return(self, tickers, reference_date):
        date_end = reference_date - timedelta(days=1)
        date_start = date_end - timedelta(days=6)

        query = f"""
        SELECT ticker, return_value
        FROM Returns
        WHERE date BETWEEN ? AND ?
        AND ticker IN ({','.join('?' for _ in tickers)})
        """
        df = pd.read_sql_query(query, self.conn, params=[date_start.strftime("%Y-%m-%d"), date_end.strftime("%Y-%m-%d")] + tickers)
        if df.empty:
            return 0.0
        return df.groupby("ticker")["return_value"].sum().mean()

    def update_portfolio(self, portfolio_id, old_ids, new_tickers, portfolio_type, date, rebalancing_id):
        manager_id = self.get_manager_id(portfolio_type)
        old_tickers = [self.product_id_to_ticker.get(pid) for pid in old_ids]
        new_ids = [self.ticker_to_product_id[tk] for tk in new_tickers if tk in self.ticker_to_product_id]

        to_sell = list(set(old_tickers) - set(new_tickers))
        to_buy = list(set(new_tickers) - set(old_tickers))

        print(f"\n📆 {date} | Portefeuille {portfolio_id} ({portfolio_type})")
        if to_buy:
            print("🟢 Acheter :", ", ".join(to_buy))
        if to_sell:
            print("🔻 Vendre :", ", ".join(to_sell))
        if not to_buy and not to_sell:
            print("✅ Aucun changement.")

        for tk in to_sell:
            self.updater.insert_deal(rebalancing_id, date, manager_id, portfolio_id, actif_vendu=tk)
        for tk in to_buy:
            self.updater.insert_deal(rebalancing_id, date, manager_id, portfolio_id, actif_achete=tk)

        rendement_moyen = self.compute_mean_return(new_tickers, datetime.strptime(date, "%Y-%m-%d"))

        self.updater.insert_portfolio_snapshot(
            rebalancing_id,
            date,
            portfolio_id,
            manager_id,
            portfolio_type,
            new_ids,
            rendement_moyen
        )

    def run_strategie(self, start_date_str, end_date_str):
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")

        self.cursor.execute("SELECT portfolio_id, nom_portefeuille FROM Portfolios")
        portfolios = self.cursor.fetchall()

        current_date = start_date
        rebalancing_id = 1

        while current_date <= end_date:
            if current_date.day == 1:
                print(f"\n======= 📅 STRATÉGIE - {current_date.strftime('%B %Y')} =======")

                for portfolio_id, portfolio_type in portfolios:
                    product_ids = self.get_range_product_ids(portfolio_id)
                    df_returns = self.get_last_30d_returns(product_ids, current_date)
                    selected_tickers = self.select_top_assets_with_moving_average(df_returns)
                    current_assets = self.get_current_assets(portfolio_id, current_date)

                    self.update_portfolio(
                        portfolio_id,
                        current_assets,
                        selected_tickers,
                        portfolio_type,
                        current_date.strftime("%Y-%m-%d"),
                        rebalancing_id
                    )

                self.updater.commit()
                rebalancing_id += 1

            current_date += timedelta(days=1)

if __name__ == "__main__":
    engine = StrategyEngine()
    engine.run_strategie("2020-01-01", "2024-12-31")
