#!/usr/bin/env python

import pandas as pd
import toml
from DataManagerClass import DataManager
from colorama import Fore as fg
import trade_bot_lib as t

class DataLoadingTester:
    def __init__(self, config_file='trading_bot_config.toml'):
        with open(config_file, 'r') as f: self.config = toml.load(f)

        self.data_manager = DataManager(config_file)
        self.window_size = self.config['strategy']['lookback_period']
        self.trading_pair = self.config['general']['trading_pair']
        self.exchange = self.config['general']['exchange']
        self.start_date = self.config['data']['start_date']
        self.end_date = self.config['data']['end_date']
        self.live = self.config['general']['live']

        self.data = self.load_full_csv()

    def load_full_csv(self):
        """
        Loads the entire CSV file using the DataManager class.
        """
        self.data_manager.load_data(
            source='csv',
            trading_pair=self.trading_pair,
            window_size=self.window_size,  # Set to None to load all data
            start_date=self.start_date,   # Set to None to load from the beginning
            end_date=self.end_date      # Set to None to load until the end
        )
        data = self.data_manager.get_data()
        print(f"Loaded full CSV file. Total rows: {len(data)}")
        return data

    def test_data_loading(self, **kwargs):
        live = kwargs.get('live', self.live)
        exchange = kwargs.get('exchange', self.exchange)

        if live:
            source = 'live'
            if exchange == "kraken":
                self.data_manager._setup_kraken_api()
            elif exchange == "coinbase":
                self.data_manager._setup_coinbase_api()
            else:
                exchange = None
        else:
            source = 'csv'

        self.data_manager.load_data(
            source=source,
            exchange=exchange,
            trading_pair=self.config['general']['trading_pair'],
            window_size=self.config['strategy']['lookback_period'],
            start_date=self.config['data']['start_date'],
            end_date=self.config['data']['end_date']
        )

        data = self.data_manager.get_data()

        self.assertIsNotNone(data)
        self.assertGreater(len(data), 0)

        required_columns = ['open', 'high', 'low', 'close', 'volume']
        for column in required_columns:
            self.assertIn(column, data.columns)

        first_timestamp = data.index[0]
        self.assertIsInstance(first_timestamp, pd.Timestamp)

        print(f"Data successfully fetched and validated for source: {source}, exchange: {exchange}")
        print(data)

    def create_rolling_window(self, window_size=None):
        """
        Creates a rolling window of specified size that slides through the entire dataset.

        :param window_size: Size of the rolling window (default is None, which uses the config value)
        :yield: Each window as a pandas DataFrame
        """
        if window_size is None:
            window_size = self.window_size

        if len(self.data) < window_size:
            raise ValueError(f"Not enough data for the specified window size ({window_size})")

        for i in range(len(self.data) - window_size + 1):
            yield self.data.iloc[i:i+window_size]

    def test_rolling_window(self, **kwargs):
        live = kwargs.get('live', False)
        exchange = kwargs.get('exchange', 'kraken')
        max_windows = kwargs.get('max_windows', 3)
        window_locations = kwargs.get('window_locations', [0,1])

        print(f"\nTesting rolling window with size {self.window_size}")
        m=0
        for i, window in enumerate(self.create_rolling_window()):
            if i >= window_locations[0] and i < window_locations[0]+window_locations[1]:
                print(f"Window {i}:")
                print(window)
                print("\n")
                m +=1
            if m == max_windows - 1:
                print(f"Printed {max_windows} windows. {len(self.data) - self.window_size + 1 - max_windows} windows remaining.")
                break

    def get_windows_count(self, **kwargs):
        return self.data_manager.get_windows_count()
        # total_rows = len(self.data)
        # total_windows = int(total_rows / self.window_size)


        print(f"Total rows in full data: {total_rows}")
        print(f"Window size: {self.window_size}")
        print(f"Total number of windows: {total_windows}")

    def assertIsNotNone(self, value, message="Value is None"):
        if value is None:
            raise AssertionError(message)

    def assertGreater(self, value1, value2, message=None):
        if not value1 > value2:
            default_message = f"Expected |{value1}| to be greater than |{value2}|"
            raise AssertionError(message or default_message)

    def assertIn(self, item, container, message=None):
        if item not in container:
            default_message = f"Expected |{item}| to be in |{container}|"
            raise AssertionError(message or default_message)

    def assertIsInstance(self, obj, cls, message=None):
        if not isinstance(obj, cls):
            default_message = f"Expected |{obj}| to be an instance of |{cls.__name__}|"
            raise AssertionError(message or default_message)


def header(txt,**kwargs):
    clr = kwargs.get('clr',fg.CYAN)
    str = f"""
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ {txt}
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
"""
    print(clr + str)

if __name__ == '__main__':
    tester = DataLoadingTester()

    header("Load CSV",clr=fg.LIGHTYELLOW_EX)
    print(tester.data)

    exit()


    header("Load CSV and get latest window",clr=fg.LIGHTYELLOW_EX)
    tester.test_data_loading(live=False)

    header("Load latest window of live data from Kraken",clr=fg.MAGENTA)
    tester.test_data_loading(live=True, exchange="kraken")

    header("Load latest window of live data from Coinbase",clr=fg.YELLOW)
    tester.test_data_loading(live=True, exchange="coinbase")

    header(f"Testing rolling window with size {tester.window_size}",clr=fg.RED)
    tester.test_rolling_window(live=False, exchange="kraken", max_windows=3)

    header(f"Testing window loations 0 and 30",clr=fg.LIGHTGREEN_EX)
    tester.test_rolling_window(live=False, exchange="kraken", max_windows=3, window_locations=[0,1])
    tester.test_rolling_window(live=False, exchange="kraken", max_windows=3, window_locations=[30,2])

    header(f"Get window count",clr=fg.LIGHTCYAN_EX)
    print(tester.get_windows_count())


    print(fg.RESET)