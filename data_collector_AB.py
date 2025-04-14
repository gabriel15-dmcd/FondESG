import os
import sys
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
from tqdm import tqdm

current_dir = os.getcwd()
sys.path.append(os.path.join(current_dir, 'Data'))

from full_dict import full_dict, full_sectors_dict

class MarketDataDownloader:
    def __init__(self, start_date='2010-01-01', end_date='2020-12-31', output_file='./Data/actifs_base.csv'):
        self.start_date = start_date
        self.end_date = end_date
        self.tickers = list(full_dict.keys())
        self.output_file = output_file

    def delete_existing_file(self):
        if os.path.exists(self.output_file):
            os.remove(self.output_file)

    def download_data(self):
        data = yf.download(self.tickers, start=self.start_date, end=self.end_date, auto_adjust=False)['Adj Close']
        return data.ffill().pct_change().replace([np.inf, -np.inf], 0)

    def get_esg_scores_yahoo(self, ticker):
        stock = yf.Ticker(ticker)
        try:
            sustainability = stock.sustainability
            if sustainability.empty:
                return None, None, None, None
            else:
                total_esg = sustainability.loc['totalEsg'].iloc[0]
                environment_score = sustainability.loc['environmentScore'].iloc[0]
                social_score = sustainability.loc['socialScore'].iloc[0]
                governance_score = sustainability.loc['governanceScore'].iloc[0]
                return environment_score, social_score, governance_score, total_esg
        except Exception as e:
            print(f"Erreur lors de la récupération des données ESG pour {ticker}: {e}")
            return None, None, None, None

    def compute_metrics(self, data):
        results = []
        for ticker in tqdm(self.tickers):
            if ticker in data.columns:
                prix = data[ticker].dropna()
                rendement_moyen = prix.mean() * 252
                volatilite_annualisee = prix.std() * np.sqrt(252)

                score_environment, score_social, score_governance, score_total = self.get_esg_scores_yahoo(ticker)

                if score_total is not None:
                    results.append({
                        'ticker': ticker,
                        'actif': full_dict[ticker],
                        'secteur': full_sectors_dict.get(ticker, 'Unknown'),
                        'rendement_moyen': rendement_moyen,
                        'volatilite_annualisee': volatilite_annualisee,
                        'score_environment': score_environment,
                        'score_social': score_social,
                        'score_governance': score_governance,
                        'score_total': score_total
                    })
        return pd.DataFrame(results)

    def save_to_csv(self, df):
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
        df.to_csv(self.output_file, index=False)
        print(f"Données sauvegardées dans {self.output_file}")

    def run(self):
        self.delete_existing_file()
        data = self.download_data()
        df_metrics = self.compute_metrics(data)
        self.save_to_csv(df_metrics)

if __name__ == "__main__":
    downloader = MarketDataDownloader()
    downloader.run()
