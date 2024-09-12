"""
This class implements a trading strategy based on technical indicators and sentiment analysis.
It uses a combination of moving averages, RSI, and sentiment scores to generate buy/sell signals.
The strategy parameters can be configured via a TOML config file or passed as keyword arguments.

Key features:
- Calculates technical indicators (SMA, EMA, RSI)
- Incorporates sentiment analysis
- Generates trading signals based on indicator crossovers and thresholds
- Supports both historical backtesting and live trading modes
- Configurable strategy parameters


"""


import pandas as pd
import numpy as np
from colorama import Fore as fg, Back as bg
from SentimentClass import OHLCSentimentAnalyzer
from pprint import pprint
import pandas as pd
import torch
import torch.nn.functional as F
import trade_bot_lib as t
import toml

class TholonicStrategy:
    def __init__(self, ohlc_data=None, sentiment=None, **kwargs):
        self.sentiment = sentiment
        self.configfile = kwargs.get('configfile',"trading_bot_config.toml")

        # Load configuration from TOML file
        with open(self.configfile, 'r') as config_file: config = toml.load(config_file)

        # override parameters from kwargs, else, use config values
        self.trading_pair           = kwargs.get('trading_pair',          config['datamanager']['trading_pair'])
        self.lookback_period        = kwargs.get('lookback_period',       config['cfg']['lookback_period'])
        self.livemode               = kwargs.get('livemode',              config['datamanager']['livemode'])
        self.negotiation_threshold  = kwargs.get('negotiation_threshold', config['cfg']['negRange'][0])
        self.limitation_multiplier  = kwargs.get('limitation_multiplier', config['cfg']['limRange'][0])
        self.contribution_threshold = kwargs.get('contribution_threshold',config['cfg']['conRange'][0])

        self.data = pd.DataFrame(ohlc_data)

    def update_data(self):
        if self.livemode:
            new_data = self.fetch_ohlcv(self.trading_pair, '1m', limit=self.lookback)
            if self.data.empty:
                self.data = new_data
            else:
                self.data = pd.concat([self.data, new_data]).drop_duplicates().sort_index().tail(self.lookback)

    def calculate_volatility(self, window=16, **kwargs):
        select = kwargs.get('volatility_method', 'parkinsons')

        if select == 'parkinsons':

            # Calculate Parkinson's volatility
            high_low_ratio = np.log(self.data['high'] / self.data['low'])
            parkinsons_volatility = np.sqrt((1 / (4 * np.log(2))) * high_low_ratio**2)

            # Annualize the volatility (assuming daily data)

            # 8760 = 24*365 because in crypto trading occurs 24 hours a day, and 365 days in a year
            annualization_factor = np.sqrt(8760)  # For crypto markets
            self.data['volatility'] = parkinsons_volatility * annualization_factor

            # Calculate rolling average volatility
            self.data['average_volatility'] = self.data['volatility'].rolling(window=window).mean()

            # Fill NaN values
            self.data['volatility'] = self.data['volatility'].bfill()
            self.data['average_volatility'] = self.data['average_volatility'].bfill()

            """
            # 2. Parkinson's volatility (based on high-low range)
            if 'high' in data.columns and 'low' in data.columns:
                data['volatility'] = np.sqrt(1 / (4 * np.log(2)) *
                                                    ((np.log(data['high'] / data['low'])**2) / 8760).rolling(window=len(data)).mean())
            """

        #! the following did not work for one reason or another
        elif select == 'garman_klass':

            # Calculate Garman-Klass volatility
            log_hl = (np.log(self.data['high'] / self.data['low']))**2
            log_co = (np.log(self.data['close'] / self.data['open']))**2

            garman_klass = 0.5 * log_hl - (2 * np.log(2) - 1) * log_co

            # Annualize the volatility (assuming hourly data)
            annualization_factor = np.sqrt(8760)  # For 24/7 crypto markets
            self.data['volatility'] = np.sqrt(garman_klass) * annualization_factor

            # Calculate rolling average volatility
            self.data['average_volatility'] = self.data['volatility'].rolling(window=window).mean()

            # Fill NaN values
            self.data['volatility'] = self.data['volatility'].bfill()
            self.data['average_volatility'] = self.data['average_volatility'].bfill()
            """
    `       # 3. Garman-Klass volatility (uses open, high, low, close)
            if all(col in data.columns for col in ['open', 'high', 'low']):
                log_hl = (np.log(data['high'] / data['low']))**2
                log_co = (np.log(data['close'] / data['open']))**2
                data['volatility'] = np.sqrt((0.5 * log_hl - (2 * np.log(2) - 1) * log_co).rolling(window=len(data)).mean() * 8760)
`            """

        elif select == 'common':

            # Calculate returns
            self.data['returns'] = self.data['close'].pct_change()

            # Calculate rolling volatility
            # 8760 = 24*365 because in crypto trading occurs 24 hours a day, and 365 days in a year
            annualization_factor = np.sqrt(8760)
            self.data['volatility'] = self.data['returns'].rolling(window=window).std() * annualization_factor

            # Calculate average volatility
            self.data['average_volatility'] = self.data['volatility'].expanding().mean()

            # print("VOL:",self.data['volatility'].iloc[-1])
            # print("AVG:",self.data['average_volatility'].iloc[-1])

            # Fill NaN values using bfill() instead of fillna(method='bfill')
            self.data['volatility'] = self.data['volatility'].bfill()
            self.data['average_volatility'] = self.data['average_volatility'].bfill()

        elif select == 'yangzhang':
            pass
            """
            # 4. Yang-Zhang volatility (combines overnight and trading day volatility)
            if all(col in data.columns for col in ['open', 'high', 'low']):
                log_oc = np.log(data['open'] / data['close'].shift(1))**2
                log_co = np.log(data['close'] / data['open'])**2
                log_hc = np.log(data['high'] / data['close'])**2
                log_cl = np.log(data['low'] / data['close'])**2
                rs = log_oc.rolling(window=len(data)).mean()
                ro = 0.5 * log_co.rolling(window=len(data)).mean() - (2 * np.log(2) - 1) * (log_hc.rolling(window=len(data)).mean() + log_cl.rolling(window=len(data)).mean())
                data['volatility'] = np.sqrt((rs + ro) * 8760)
            """
        elif select == 'ewma':
            pass
            """
            # 5. Exponentially Weighted Moving Average (EWMA) volatility
            data['volatility'] = data['returns'].ewm(span=len(data), adjust=False).std() * np.sqrt(8760)
            """
        else:
            raise ValueError(f"Invalid volatility method: {select}")
            exit(2)

    def calculate_indicators(self):
        # Price change remains the same as it's calculated per row (old comment, but I have no idea what I was referring to :/ )
        self.data['price_change'] = (self.data['close'] - self.data['open']) / self.data['open'] * 100

        # Use the mean of all volume data in the set
        self.data['average_volume'] = self.data['volume'].mean()

        # Calculate volatility as the standard deviation of all close prices in the set
        self.calculate_volatility(volatility_method='parkinsons')

    def calculate_indicators_torch(self, data_tensor):
        # Unpack columns
        open_price, high, low, close, volume = data_tensor.unbind(1)

        # Calculate price change
        price_change = (close - open_price) / open_price * 100
        data_tensor = torch.cat([data_tensor, price_change.unsqueeze(1)], dim=1)

        # Calculate average volume
        avg_volume = volume.mean().expand(volume.shape[0], 1)
        data_tensor = torch.cat([data_tensor, avg_volume], dim=1)

        # Calculate volatility (Garman-Klass)
        log_hl = torch.log(high / low).pow(2)
        log_co = torch.log(close / open_price).pow(2)
        volatility = torch.sqrt(0.5 * log_hl - (2 * torch.log(torch.tensor(2.)) - 1) * log_co)
        annualization_factor = torch.sqrt(torch.tensor(8760.))
        volatility *= annualization_factor
        data_tensor = torch.cat([data_tensor, volatility.unsqueeze(1)], dim=1)

        # Calculate average volatility using cumulative sum and division
        cumsum_volatility = torch.cumsum(volatility, dim=0)
        lookback_tensor = torch.arange(1, len(volatility) + 1, device=data_tensor.device).float().clamp(max=self.lookback)
        avg_volatility = cumsum_volatility / lookback_tensor
        data_tensor = torch.cat([data_tensor, avg_volatility.unsqueeze(1)], dim=1)

        return data_tensor

    def generate_signals(self):
        self.data['negotiation_condition'] = self.data['price_change'] >= self.negotiation_threshold
        self.data['limitation_condition'] = self.data['volume'] >= self.data['average_volume'] * self.limitation_multiplier
        self.data['contribution_condition'] = self.data['volatility'] <= self.data['average_volatility'] * self.contribution_threshold
        self.data['buy_condition'] = (
            self.data['negotiation_condition'] &
            self.data['limitation_condition'] &
            self.data['contribution_condition']
        )
        self.data['sell_condition'] = (
            (self.data['volatility'] < self.data['average_volatility']) &
            (self.data['volatility'].shift(1) >= self.data['average_volatility'].shift(1))
        )

        #TODO  why is this here AFTER setting the sell_condition?
        self.data['volatility'] <= self.data['average_volatility'] * self.contribution_threshold


    def generate_signals_torch(self, data_tensor):
        price_change, volume, avg_volume, volatility, avg_volatility = data_tensor[:, -5:].unbind(1)

        negotiation_condition = price_change >= self.negotiation_threshold
        limitation_condition = volume >= avg_volume * self.limitation_multiplier
        contribution_condition = volatility <= avg_volatility * self.contribution_threshold

        buy_condition = negotiation_condition & limitation_condition & contribution_condition
        sell_condition = (volatility < avg_volatility) & (F.pad(volatility, (1, 0))[:-1] >= F.pad(avg_volatility, (1, 0))[:-1])

        data_tensor = torch.cat([
            data_tensor,
            negotiation_condition.unsqueeze(1).float(),
            limitation_condition.unsqueeze(1).float(),
            contribution_condition.unsqueeze(1).float(),
            buy_condition.unsqueeze(1).float(),
            sell_condition.unsqueeze(1).float()
        ], dim=1)

        return data_tensor

    def print_data_info(self):
        """
        Print information about the data, including its sentiment.
        """
        print("Summary statistics of the data:")
        print(self.data)
        print(f"\nOverall sentiment: {self.sentiment}")

        """
        Analyze sentiment of OHLC data over a given window size.

        :param window_size: int, number of periods to consider for each sentiment analysis
        :return: pandas Series of sentiment labels
        """
        window_size = len(self.data)


    def backtest(self, initial_position=0):
        position = initial_position
        trades = []

        for i, row in self.data.iterrows():
            sentiment = row['sentiment']
            close = row['close']
            isBuy = row['buy_condition']
            isSell = row['sell_condition']

            doBuy = position == 0 and isBuy
            if doBuy:
                position = 1
                tary = {'entry_date': i, 'entry_price': close, 'entry_sentiment': sentiment}
                trades.append(tary)

            doSell = position == 1 and isSell
            if doSell:
                if trades:
                    position = 0
                    tary = {'exit_date': i, 'exit_price': close, 'exit_sentiment': sentiment}
                    trades[-1].update(tary)
                else:
                    print("  WARNING: Attempted to sell without any prior buys. Ignoring this sell signal.")

        return trades, position  # Return the final position along with trades


    def calculate_performance(self, trades):
        if trades.empty:  # Check if trades list is empty
            # print("No trades executed")
            return None

        # Convert trades list to DataFrame if it's not already
        if isinstance(trades, list):
            trades = pd.DataFrame(trades)

        # Check if 'exit_price' exists in the DataFrame
        if 'exit_price' not in trades.columns:
            # print("No completed trades found")
            return None

        # Filter out incomplete trades
        completed_trades = trades.dropna(subset=['exit_price'])

        if completed_trades.empty:
            # print("No completed trades found")
            return None

        completed_trades['return'] = (completed_trades['exit_price'] - completed_trades['entry_price']) / completed_trades['entry_price']
        total_return = (completed_trades['return'] + 1).prod() - 1
        num_trades = len(completed_trades)
        win_rate = (completed_trades['return'] > 0).mean()

        inon = completed_trades['entry_sentiment'].iloc[0]
        outon = completed_trades['exit_sentiment'].iloc[-1]

        buy_and_hold_return = (self.data['close'].iloc[-1] - self.data['close'].iloc[0]) / self.data['close'].iloc[0]
        strat_over_hodl = total_return - buy_and_hold_return

        return {
            'Return': total_return,
            'Trades': num_trades,
            'Profit': win_rate,
            'StratOverHodl': strat_over_hodl,
            'inon': inon,
            'outon': outon,
        }

    def show_data(self,data):
        # print(self.data.index) # useless
        print("-------------------------------------------------------------------- df.head()")
        print(data.head())
        print("-------------------------------------------------------------------- df.info()")
        print(data.info())
        print("-------------------------------------------------------------------- df.types()")
        print(data.dtypes)
        print("-------------------------------------------------------------------- df.describe()")
        print(data.describe())
        print("-------------------------------------------------------------------- df.todict")
        pprint(self.data.to_dict()) #too long
        print("-------------------------------------------------------------------- df")
        pprint(self.data) # INCOMPLETE
        print("-------------------------------------------------------------------- df.index")
        print(self.data.index) #useless
        print("-------------------------------------------------------------------- df.values")
        print(self.data.values) # unreadablke
        print("-------------------------------------------------------------------- df.head()")
        print(self.data.head()) #useless
        print("-------------------------------------------------------------------- df.tail()")
        print(self.data.tail()) #useless
        print("-------------------------------------------------------------------- df.tail()")
        # exit()


    def run_strategy(self):
        # self.update_data()   #TODO  needed for live only

        min_volume = 5000 # only look at volumes above this
        if self.data['volume'].iloc[-1] * self.data['close'].iloc[-1] < min_volume:
            print(f"{self.trading_pair:10s}:Volume is too low: {int(self.data['volume'].iloc[-1]):8d} * {self.data['close'].iloc[-1]:8.2f} = {int(self.data['volume'].iloc[-1] * self.data['close'].iloc[-1]):8d}")
            exit()

        self.calculate_indicators()
        self.generate_signals()
        self.data['sentiment'] =self.sentiment

        # Get the latest data
        latest_data = self.data.iloc[-1].copy()

        return latest_data, self.data


    def run_strategy_torch(self):
        # Convert DataFrame to PyTorch tensor and move to GPU
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        data_tensor = torch.tensor(self.data.values, dtype=torch.float32, device=device)

        # Calculate indicators
        data_tensor = self.calculate_indicators_torch(data_tensor)

        # Generate signals
        data_tensor = self.generate_signals_torch(data_tensor)

        # Analyze sentiment
        sentiment_analyzer = OHLCSentimentAnalyzer(self.apiout)
        sentiment_tensor = sentiment_analyzer.analyze_torch(data_tensor)

        # Move results back to CPU and update DataFrame
        cpu_data = data_tensor.cpu().numpy()

        # Create a new DataFrame with the original columns plus the new ones
        columns = list(self.data.columns) + [
            'price_change', 'average_volume', 'volatility', 'average_volatility',
            'negotiation_condition', 'limitation_condition', 'contribution_condition',
            'buy_condition', 'sell_condition'
        ]

        self.data = pd.DataFrame(cpu_data, columns=columns, index=self.data.index)

        # Convert boolean columns back to bool type
        bool_columns = ['negotiation_condition', 'limitation_condition', 'contribution_condition', 'buy_condition', 'sell_condition']
        self.data[bool_columns] = self.data[bool_columns].astype(bool)

        # Add sentiment column
        self.data['sentiment'] = sentiment_tensor.cpu().numpy()

        # Get the latest data
        latest_data = self.data.iloc[-1].copy()

        return latest_data, self.data

