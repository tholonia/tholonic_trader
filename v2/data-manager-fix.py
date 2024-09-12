import pandas as pd
import ccxt
from datetime import datetime, timedelta
import toml

class DataManager:
    def __init__(self, config_file='trading_bot_config.toml'):
        self.config = self.load_config(config_file)
        self.data = None
        self.data_source = self.config['data']['source']
        self.exchange = None
        self.window_size = self.config['strategy']['lookback_period']
        self.trading_pair = self.config['general']['trading_pair']

    # ... (other methods remain the same)

    def _load_csv_data(self, trading_pair, window_size, start_date, end_date):
        filename = self.config['data']['csv_file']
        df = pd.read_csv(filename, parse_dates=['Date'])

        print("Full DataFrame:")
        print(df)
        print("\nDataFrame info:")
        print(df.info())
        print("\nFirst few rows:")
        print(df.head())
        print("\nLast few rows:")
        print(df.tail())

        if start_date and end_date:
            df = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]

        print("\nAfter date filtering:")
        print(df)

        self.data = df.tail(window_size)

        print("\nFinal data:")
        print(self.data)

    # ... (rest of the class remains the same)