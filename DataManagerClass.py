import pandas as pd
import ccxt
from datetime import datetime, timedelta
import toml
import trade_bot_lib as t

class DataManager:
    def __init__(self, config_file='trading_bot_config.toml'):
        self.config       = self.load_config(config_file)
        self.data_source  = self.config['datamanager']['source']
        self.exchange     = self.config['datamanager']['exchange']
        self.window_size  = self.config['datamanager']['window_size']
        self.trading_pair = self.config['datamanager']['trading_pair']
        self.start_date   = self.config['datamanager']['start_date']
        self.end_date     = self.config['datamanager']['end_date']
        self.exchange     = self.config['datamanager']['exchange']

        self.data = None #self.load_data()
        # print(self.data)
        # exit()
    def load_config(self, config_file):
        with open(config_file, 'r') as f:
            return toml.load(f)

    def load_full_csv(self):
        """
        Loads the entire CSV file using the DataManager class.
        """
        self.load_data(
            source='csv',
            trading_pair=self.trading_pair,
            window_size=self.window_size,  # Set to None to load all data
            start_date=self.start_date,   # Set to None to load from the beginning
            end_date=self.end_date      # Set to None to load until the end
        )
        data = self.get_data()
        print(f"Loaded full CSV file. Total rows: {len(data)}")
        return data


    def load_data(self, **kwargs):
        source       = kwargs.get('source',      self.config['datamanager']['source'])
        exchange     = kwargs.get('exchange',    self.config['datamanager']['exchange'])
        trading_pair = kwargs.get('trading_pair',self.config['datamanager']['trading_pair'])
        window_size  = kwargs.get('window_size', self.config['datamanager']['window_size'])
        start_date   = kwargs.get('start_date',  self.config['datamanager']['start_date'])
        end_date     = kwargs.get('end_date',    self.config['datamanager']['end_date'])
        timeframe    = kwargs.get('timeframe',   self.config['datamanager'].get('timeframe', '1h'))


        if source == 'csv': # assumes backtest mode
            self._load_csv_data(trading_pair, window_size, start_date, end_date)
        else: # live mode
            if self.config['datamanager']['exchange'] == "kraken":
                self._setup_kraken_api()
            elif self.config['datamanager']['exchange'] == "coinbase":
                self._setup_coinbase_api()
            self.data = self._load_live_data(trading_pair, window_size, timeframe)

    def _load_csv_data(self, trading_pair, window_size, start_date, end_date):
        filename = self.config['datamanager']['csv_file']
        df = pd.read_csv(filename, parse_dates=['timestamp'], index_col='timestamp')

        # print("Full DataFrame:")
        # print(df)
        # print("\nDataFrame info:")
        # print(df.info())

        if df.empty:  # Check for an empty DataFrame
            raise ValueError("CSV file is empty")

        if start_date and end_date:
            df = df.loc[start_date:end_date]


        # print("\nAfter date filtering:")
        # print(df)

        if len(df) < window_size:
            raise ValueError(f"Not enough data ({len(df)}) for the specified window size ({window_size})")

        # self.data = df.tail(window_size)
        self.data = df

        # print("\nFinal data:")
        # print(self.data)

    def _setup_kraken_api(self):
        self.exchange = ccxt.kraken({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
    def _setup_coinbase_api(self):
        self.exchange = ccxt.coinbase({
            'enableRateLimit': True,  # Ensure rate limiting to avoid being blocked
        })

    def _load_live_data(self, trading_pair, window_size, timeframe):
        try:
            ohlcv = self.exchange.fetch_ohlcv(trading_pair, timeframe, limit=window_size)
            if not ohlcv:
                raise ValueError("No data returned from the exchange.")


            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            # df = pd.DataFrame(ohlcv, columns=['Date', 'Open', 'High', 'Low', 'close', 'Volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            return df
        except Exception as e:
            print(f"Error fetching live data: {e}")
            return None

    def get_latest_data(self):
        return self.data

    def get_windows_count(self):
        return int(len(self.data) / self.window_size)

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

    def get_rolling_window(self, **kwargs):
        max_windows = kwargs.get('max_windows', 3)
        window_locations = kwargs.get('window_locations', [0,1])

        m=0
        for i, window in enumerate(self.create_rolling_window()):
            if i >= window_locations[0] and i < window_locations[0]+window_locations[1]:
                return window

    def update_data(self):
        if self.data_source == 'exchange':
            last_timestamp = self.data.index[-1]
            new_data = self._load_live_data(self.trading_pair, 1, self.config['data'].get('timeframe', '1h'))
            if new_data is not None and not new_data.empty and new_data.index[0] > last_timestamp:
                self.data = pd.concat([self.data.iloc[1:], new_data])
        elif self.data_source == 'csv':
            # Simulate moving forward by one candle, modify with realistic changes
            new_row = self.data.iloc[-1:].copy()
            new_row.index = new_row.index + pd.Timedelta(self.config['data'].get('timeframe', '1h'))
            new_row['open'] += (new_row['close'] - new_row['open']) * 0.01  # Example adjustment
            new_row['close'] += (new_row['close'] - new_row['open']) * 0.01  # Example adjustment
            self.data = pd.concat([self.data.iloc[1:], new_row])

    def get_data(self):
        return self.data
