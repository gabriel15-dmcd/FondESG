import sys
import os
import numpy as np
import pandas as pd
import yfinance as yf

current_dir = os.getcwd()
sys.path.append(os.path.join(current_dir, 'Data'))

from full_dict import full_dict, full_sectors_dict

class DataFilteredBuilder:
    def __init__(self, start_date='2010-01-01', end_date='2024-12-31', csv_file='./Data/data_filtered.csv'):
        self.start_date = start_date
        self.end_date = end_date
        self.csv_file = csv_file
        self.tickers = list(full_dict.keys())

    def delete_existing_file(self):
        if os.path.exists(self.csv_file):
            os.remove(self.csv_file)
            print(f"Fichier existant {self.csv_file} supprimé.")

    def download_and_process_data(self):
        data = yf.download(self.tickers, start=self.start_date, end=self.end_date, auto_adjust=False)['Adj Close']
        data = data.ffill().pct_change().replace([np.inf, -np.inf], 0)
        data_filtered = data[data.index.to_series().dt.dayofweek < 5].fillna(0)
        return data_filtered

    def build_classification_df(self):
        return pd.DataFrame([{
            'id': ticker,
            'nom': full_dict[ticker],
            'secteur': full_sectors_dict.get(ticker, 'Unknown')
        } for ticker in self.tickers])

    def build_data_filtered(self, data_filtered, classification_df):
        df_long = data_filtered.reset_index().melt(id_vars='Date', var_name='id', value_name='return')
        df_long['volatilite_journaliere'] = np.sqrt(df_long['return'].abs())
        
        # Filtrer les lignes où 'return' est égal à 0
        df_long_cleaned = df_long[df_long['return'] != 0]
        
        return df_long_cleaned.merge(classification_df, on='id', how='left')

    def save_to_csv(self, df):
        os.makedirs(os.path.dirname(self.csv_file), exist_ok=True)
        df.to_csv(self.csv_file, index=False)
        print(f"Données sauvegardées dans {self.csv_file}")

    def run(self):
        self.delete_existing_file()
        data_filtered = self.download_and_process_data()
        classification_df = self.build_classification_df()
        final_df = self.build_data_filtered(data_filtered, classification_df)
        self.save_to_csv(final_df)

# Exemple d'utilisation
if __name__ == "__main__":
    builder = DataFilteredBuilder()
    builder.run()
