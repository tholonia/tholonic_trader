"""
TholonicStrategy Class

This class implements a trading strategy based on various market indicators and conditions.

Key Features:
1. Initialization with strategy parameters and data
2. Calculation of price changes, volatility, and other market metrics
3. Implementation of trading conditions based on negotiation, limitation, and contribution thresholds
4. MACD (Moving Average Convergence Divergence) calculation and sentiment analysis
5. Backtesting functionality to evaluate strategy performance

Attributes:
    trading_pair (str): The trading pair symbol (e.g., 'BTCUSD')
    lookback (int): The number of periods to look back for calculations
    negotiation_threshold (float): Threshold for the negotiation condition
    limitation_multiplier (float): Multiplier for the limitation condition
    contribution_threshold (float): Threshold for the contribution condition
    livemode (bool): Flag to indicate if running in live mode
    livemode_n_elements (int): Number of elements to consider in live mode
    macd (pandas.Series): MACD line values
    signal (pandas.Series): Signal line values
    data (pandas.DataFrame): OHLCV data for analysis

Methods:
    run_strategy(): Executes the main strategy logic
    calculate_macd(): Calculates MACD indicators
    backtest(): Performs backtesting of the strategy
    (Other helper methods for specific calculations and conditions)

Usage:
    Initialize the class with desired parameters and data, then call run_strategy()
    to execute the trading logic or backtest() to evaluate historical performance.

Note: This class is designed for algorithmic trading and should be used with caution.
Always perform thorough testing and risk assessment before using in live trading.
"""


import pandas as pd
import numpy as np
import ccxt
from colorama import Fore as fg, Back as bg
from DataLoaderClass import DataLoader
from pprint import pprint
import trade_bot_vars as v
import json
import pandas as pd
from datetime import datetime


class TholonicStrategy:
    def __init__(self, trading_pair, negotiation_threshold, limitation_multiplier,
                 contribution_threshold, lookback_period, livemode, livemode_n_elements,ohlc_data,
                #  ohlcfile, from_date, to_date
                 ):
        self.trading_pair = trading_pair
        self.lookback = lookback_period
        self.negotiation_threshold = negotiation_threshold
        self.limitation_multiplier = limitation_multiplier
        self.contribution_threshold = contribution_threshold
        self.livemode = livemode
        self.livemode_n_elements = livemode_n_elements
        self.macd = None
        self.signal = None
        self.data = pd.DataFrame(ohlc_data)

        # if not self.livemode:
        #     loader = DataLoader(ohlcfile, from_date, to_date, self.livemode_n_elements)
        #     loader.shift_window(v.rolling_window_position)
        #     self.data = loader.get_data()
        # else:
        #     self.data = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
        #     self.data.index.name = 'timestamp'
        #     self.exchange = ccxt.kraken({
        #         'enableRateLimit': True,
        #         'options': {
        #             'defaultType': 'future'
        #         }
        #     })

    # def xxalt_fetch_ohlcv(self, symbol, timeframe):
    #     cache_key = f"{symbol}_{timeframe}"

    #     # Check if data is already cached
    #     if hasattr(v, 'ohlc_ary') and cache_key in v.ohlc_ary:
    #         cached_data = json.loads(v.ohlc_ary[cache_key])
    #         df = pd.DataFrame(cached_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    #         df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    #         df.set_index('timestamp', inplace=True)

    #         return df.tail(self.lookback)

    #     try:
    #         # Fetch OHLCV data with limit set to self.lookback
    #         ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=self.lookback)

    #         # Create DataFrame from the fetched data
    #         df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    #         df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    #         df.set_index('timestamp', inplace=True)

    #         # Ensure we only have 'lookback' number of rows
    #         df = df.tail(self.lookback)

    #         # Cache the data
    #         if not hasattr(v, 'ohlc_ary'):
    #             v.ohlc_ary = {}
    #         v.ohlc_ary[cache_key] = json.dumps(df.reset_index().to_dict('records'))

    #         return df
    #     except Exception as e:
    #         print(f"Error fetching OHLCV data: {e}")
    #         return pd.DataFrame()  # Return an empty DataFrame in case of error

    # def xxfetch_ohlcv(self, symbol, timeframe):
    #     print(">>>..........................",v.rolling_window_position)
    #     exit()
    #     try:
    #         # Fetch OHLCV data with limit set to self.lookback
    #         ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=self.lookback)

    #         # Create DataFrame from the fetched data
    #         df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    #         df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    #         df.set_index('timestamp', inplace=True)

    #         # Ensure we only have 'lookback' number of rows
    #         df = df.tail(self.lookback)  #takes an extra 2s for 10000 records

    #         return df
    #     except Exception as e:
    #         print(f"Error fetching OHLCV data: {e}")
    #         return pd.DataFrame()  # Return an empty DataFrame in case of error


    def update_data(self):
        if self.livemode:
            new_data = self.fetch_ohlcv(self.trading_pair, '1m', limit=self.lookback)
            if self.data.empty:
                self.data = new_data
            else:
                self.data = pd.concat([self.data, new_data]).drop_duplicates().sort_index().tail(self.lookback)

    def xxcalculate_indicators(self):
        self.data['price_change'] = (self.data['close'] - self.data['open']) / self.data['open'] * 100
        self.data['average_volume'] = self.data['volume'].rolling(window=self.lookback).mean()
        self.data['volatility'] = self.data['close'].rolling(window=self.lookback).std()
        self.data['average_volatility'] = self.data['volatility'].rolling(window=self.lookback).mean()


    def calculate_volatility(self, window=16):
        """
        Calculate simple volatility and average volatility, and update the DataFrame.

        :param window: int, the rolling window for volatility calculation (default 16)
        """
        # Calculate returns
        self.data['returns'] = self.data['close'].pct_change()

        # Calculate rolling volatility
        self.data['volatility'] = self.data['returns'].rolling(window=window).std() * np.sqrt(8760)



        # Calculate average volatility
        self.data['average_volatility'] = self.data['volatility'].expanding().mean()

        print("VOL:",self.data['volatility'].iloc[-1])
        print("AVG:",self.data['average_volatility'].iloc[-1])

        # Fill NaN values using bfill() instead of fillna(method='bfill')
        self.data['volatility'] = self.data['volatility'].bfill()
        self.data['average_volatility'] = self.data['average_volatility'].bfill()

    def calculate_parkinsons_volatility(self, window=16):
        """
        Calculate Parkinson's volatility and average volatility, and update the DataFrame.

        :param window: int, the rolling window for volatility calculation (default 16)
        """
        # Calculate Parkinson's volatility
        high_low_ratio = np.log(self.data['high'] / self.data['low'])
        parkinsons_volatility = np.sqrt((1 / (4 * np.log(2))) * high_low_ratio**2)

        # Annualize the volatility (assuming daily data)
        annualization_factor = np.sqrt(8760)  # For crypto markets
        self.data['volatility'] = parkinsons_volatility * annualization_factor

        # Calculate rolling average volatility
        self.data['average_volatility'] = self.data['volatility'].rolling(window=window).mean()

        # Fill NaN values
        self.data['volatility'] = self.data['volatility'].bfill()
        self.data['average_volatility'] = self.data['average_volatility'].bfill()

    def calculate_garman_klass_volatility(self, window=16):
        """
        Calculate Garman-Klass volatility and average volatility, and update the DataFrame.

        :param window: int, the rolling window for average volatility calculation (default 16)
        """
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





    def calculate_indicators(self):
        # Price change remains the same as it's calculated per row
        self.data['price_change'] = (self.data['close'] - self.data['open']) / self.data['open'] * 100

        # Use the mean of all volume data in the partition
        self.data['average_volume'] = self.data['volume'].mean()

        # Calculate volatility as the standard deviation of all close prices in the partition
        # self.calculate_volatility() #! works
        self.calculate_parkinsons_volatility() # ~works
        # self.calculate_garman_klass_volatility() # !works

        # Correct Annualization Factor:
        # For daily data: Use √365 instead of √252.
        # For hourly data: Use √(365 * 24) = √8760.
        # For minute data: Use √(365 * 24 * 60) = √525,600.


        # # 2. Parkinson's volatility (based on high-low range)
        # if 'high' in data.columns and 'low' in data.columns:
        #     data['volatility'] = np.sqrt(1 / (4 * np.log(2)) *
        #                                         ((np.log(data['high'] / data['low'])**2) / 8760).rolling(window=len(data)).mean())

        # # 3. Garman-Klass volatility (uses open, high, low, close)
        # if all(col in data.columns for col in ['open', 'high', 'low']):
        #     log_hl = (np.log(data['high'] / data['low']))**2
        #     log_co = (np.log(data['close'] / data['open']))**2
        #     data['volatility'] = np.sqrt((0.5 * log_hl - (2 * np.log(2) - 1) * log_co).rolling(window=len(data)).mean() * 8760)

        # # 4. Yang-Zhang volatility (combines overnight and trading day volatility)
        # if all(col in data.columns for col in ['open', 'high', 'low']):
        #     log_oc = np.log(data['open'] / data['close'].shift(1))**2
        #     log_co = np.log(data['close'] / data['open'])**2
        #     log_hc = np.log(data['high'] / data['close'])**2
        #     log_cl = np.log(data['low'] / data['close'])**2
        #     rs = log_oc.rolling(window=len(data)).mean()
        #     ro = 0.5 * log_co.rolling(window=len(data)).mean() - (2 * np.log(2) - 1) * (log_hc.rolling(window=len(data)).mean() + log_cl.rolling(window=len(data)).mean())
        #     data['volatility'] = np.sqrt((rs + ro) * 8760)

        # # 5. Exponentially Weighted Moving Average (EWMA) volatility
        # data['volatility'] = data['returns'].ewm(span=len(data), adjust=False).std() * np.sqrt(8760)






        # print(self.data['volatility'].iloc[-1],self.data['average_volatility'].iloc[-1])


        # Set average volatility to be the same as volatility since we're not using a rolling window
        # self.data['average_volatility'] = self.data['volatility'].mean()











        # print(">>>",self.data['volatility'].iloc[-1],self.data['average_volatility'].iloc[-1])

    # def determine_movement(self):

    def generate_signals(self):
        # self.data['signature'] = self.create_price_set_signature(self.data['close'])
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

        # if self.data['sell_condition'].iloc[-1] == True:
        #     print(">>> SELL=OK")
        #! why is this here AFTER setting the sell_condition?
        self.data['volatility'] <= self.data['average_volatility'] * self.contribution_threshold

    def analyze_summary_sentiment(self):
        open_price = self.data['open'].mean()
        close_price = self.data['close'].mean()
        high_price = self.data['high'].max()
        low_price = self.data['low'].min()

        price_change = (close_price - open_price) / open_price
        volatility = (high_price - low_price) / open_price

        if abs(price_change) < 0.02 and volatility < 0.03:
            senti= 1 #"Sideways"
        elif price_change < -0.05:
            senti= 2 #"Strong Bear"
        elif price_change < -0.02:
            senti= 3 #"Bear"
        elif price_change > 0.05:
            senti= 4 #"Strong Bull"
        elif price_change > 0.02:
            senti= 5 #"Bull"
        elif volatility > 0.04:
            senti= 6 #"High Volatility"
        elif 0.02 <= volatility <= 0.04 and abs(price_change) < 0.01:
            senti= 7 #"Neutral"
        else:
            senti= 8 #"Mixed"

        self.data['sentiment'] =senti

    def apply_sentiment_analysis(self):
        """
        Apply sentiment analysis to self.data and add results as a new attribute.
        """
        self.sentiment = self.analyze_summary_sentiment()

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


# ----
    def categorize_sentiment(self):
        opens = self.data['open']
        closes = self.data['close']
        highs = self.data['high']
        lows = self.data['low']

        price_change = (closes.iloc[-1] - opens.iloc[0]) / opens.iloc[0]
        volatility = (highs.max() - lows.min()) / opens.iloc[0]
        trend = np.polyfit(range(len(closes)), closes, 1)[0]

        body_sizes = abs(closes - opens) / opens
        average_body_size = body_sizes.mean()
        upper_wicks = (highs - np.maximum(opens, closes)) / opens
        lower_wicks = (np.minimum(opens, closes) - lows) / opens
        average_upper_wick = upper_wicks.mean()
        average_lower_wick = lower_wicks.mean()


        sensitivity_values = 1 # set level of sensitivity, 0=default, 1=more sensitive, 2=less sensitive
        if sensitivity_values == 1:
            # More sensitive values
            vs1 = [0.01, 0.02]      # Sideways
            vs2 = [-0.04, 0]        # StrongBear
            vs3 = [-0.015, 0]       # Bear
            vs4 = [0.04, 0]         # StrongBull
            vs5 = [0.015, 0]        # Bull
            vs6 = [1.5]             # StrongResistance
            vs7 = [1.5]             # StrongSupport
            vs8 = [0.03]            # HighVolatility
            vs9 = [0.015, 0.03, 0.0005]  # Neutral
        else:
            #! default sensitivities
            vs1=[0.02,0.03]       #~ Sideways,          more sensitive = Decrease  values (e.g., 0.01 and 0.02)
            vs2=[-0.05,0]         #~ StrongBear,        more sensitive = Decrease the price change threshold (e.g., -0.04)
            vs3=[-0.02,0]         #~ Bear,              more sensitive = Decrease the price change threshold (e.g., -0.01)
            vs4=[0.05,0]          #~ StrongBull,        more sensitive = Increase  values (e.g., 0.04)
            vs5=[0.02,0]          #~ Bull,              more sensitive = Increase  values (e.g., 0.01)
            vs6=[2]               #~ StrongResistance,  more sensitive = Decrease the multiplier (e.g., 1.5)
            vs7=[2]               #~ StrongSupport,     more sensitive = Decrease the multiplier (e.g., 1.5)
            vs8=[0.04]            #~ HighVolatility,    more sensitive = Decrease this threshold (e.g., 0.03)
            vs9=[0.02,0.04,0.001] #~ Neutral,           more sensitive = more sensitive: Narrow the volatility range and decrease the trend threshold


        if  abs(price_change) < vs1[0] and volatility < vs1[1]:
            sentiment =  1 #"Sideways"
        elif price_change < vs2[0] and trend < vs2[1]:
            sentiment =  2 #"Strong Bear"
        elif price_change < vs3[0] and trend < vs3[1]:
            sentiment =  3 #"Bear"
        elif price_change > vs4[0] and trend > vs4[1]:
            sentiment =  4 #"Strong Bull"
        elif price_change > vs5[0] and trend > vs5[1]:
            sentiment =  5 #"Bull"
        elif average_upper_wick > vs6[0] * average_body_size:
            sentiment =  6 #"Strong Resistance"
        elif average_lower_wick > vs7[0] * average_body_size:
            sentiment =  7 #"Strong Support"
        elif volatility > vs8[0]:
            sentiment =  8 #"High Volatility"
        elif vs9[0] <= volatility <= vs9[1] and abs(trend) < vs9[2]:
            sentiment =  9 #"Neutral"
        else:
            sentiment =  10 #"Mixed"

        self.data['sentiment'] =sentiment
#-------



    def calculate_macd_sentiment(self, fast_period=12, slow_period=26, signal_period=9, lookback=5):
        exp1 = self.data['close'].ewm(span=fast_period, adjust=False).mean()
        exp2 = self.data['close'].ewm(span=slow_period, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=signal_period, adjust=False).mean()
        histogram = macd - signal

        latest_macd = macd.iloc[-1]
        latest_signal = signal.iloc[-1]
        latest_histogram = histogram.iloc[-1]

        macd_slope = (macd.iloc[-1] - macd.iloc[-lookback]) / lookback
        signal_slope = (signal.iloc[-1] - signal.iloc[-lookback]) / lookback

        position = np.tanh((latest_macd - latest_signal) / abs(latest_macd))
        momentum = np.tanh(latest_histogram / abs(latest_macd))
        trend = np.tanh((macd_slope + signal_slope) / 2)

        sentiment = (position + momentum + trend) / 3

        return np.clip(sentiment, -1, 1)

    def calculate_macd(self, fast_period=12, slow_period=26, signal_period=9):
        # Calculate MACD
        exp1 = self.data['close'].ewm(span=fast_period, adjust=False).mean()
        exp2 = self.data['close'].ewm(span=slow_period, adjust=False).mean()
        self.macd = exp1 - exp2
        self.signal = self.macd.ewm(span=signal_period, adjust=False).mean()

        # Calculate MACD histogram
        self.macd_histogram = self.macd - self.signal

        # Add MACD components to the dataframe
        self.data['macd'] = self.macd
        self.data['macd_signal'] = self.signal
        self.data['macd_histogram'] = self.macd_histogram

        # Calculate MACD sentiment
        self.macd_sentiment = self.calculate_macd_sentiment(fast_period, slow_period, signal_period)

        # Add original MACD sentiment to the dataframe
        self.data['macd_sentiment'] = self.macd_sentiment

        # Normalize MACD sentiment to [-1, 1] range
        min_sentiment = self.macd_sentiment.min()
        max_sentiment = self.macd_sentiment.max()

        # Check if min and max are different to avoid division by zero
        # if min_sentiment != max_sentiment:
        #     normalized_sentiment = np.interp(self.macd_sentiment,
        #                                      (min_sentiment, max_sentiment),
        #                                      (0, 10))
        # else:
        #     # If all values are the same, set normalized sentiment to 0
        #     normalized_sentiment = np.zeros_like(self.macd_sentiment)

        # # Add normalized MACD sentiment to the dataframe
        # self.data['normalized_macd_sentiment'] = normalized_sentiment

        return self.macd_sentiment


    def backtest(self):
        """
        1. It iterates through the data, checking each row.
        2. If there's no current position (position == 0) and the buy condition is met, it enters a new trade.
        3. If there's an existing position (position == 1) and the sell condition is met, it exits the trade.
        4. For each trade, it records the entry and exit information, including date, price, and sentiment.

        This only supports pyramiding = 1.  For pyramiding > 1, we need to use the position average cost
        """
        trades = []
        v = type('', (), {'position': 0})()  # Simple object to hold position

        for i, row in self.data.iterrows():
            sentiment = row['sentiment']
            close = row['close']
            isBuy = row['buy_condition']
            isSell = row['sell_condition']

            # print(f"\nIteration {i}:")
            # print(f"  Position: {v.position}")
            # print(f"  Buy condition: {isBuy}")
            # print(f"  Sell condition: {isSell}")
            # print(f"  Close price: {close}")
            # print(f"  Current trades: {len(trades)}")

            doBuy = v.position == 0 and isBuy
            if doBuy:
                # print("  Executing buy...")
                v.position = 1
                tary = {'entry_date': i, 'entry_price': close, 'entry_sentiment': sentiment}
                trades.append(tary)
                # print(f"  Trade added. Total trades: {len(trades)}")

            doSell = v.position == 1 and isSell
            if doSell:
                # print("  Executing sell...")
                if trades:  # Check if there are any trades to update
                    v.position = 0
                    tary = {'exit_date': i, 'exit_price': close, 'exit_sentiment': sentiment}
                    trades[-1].update(tary)
                    # print(f"  Last trade updated. Total trades: {len(trades)}")
                else:
                    print("  WARNING: Attempted to sell without any prior buys. Ignoring this sell signal.")

        # print("\nBacktest completed.")
        # print(f"Total trades executed: {len(trades)}")
        return trades


    def calculate_performance(self, trades):

        # self.show_data(trades)
        # exit()
        if not trades.empty:
            trades['return'] = (trades['exit_price'] - trades['entry_price']) / trades['entry_price']
            total_return = (trades['return'] + 1).prod() - 1
            num_trades = len(trades)
            win_rate = (trades['return'] > 0).mean()

            inon = trades['entry_sentiment'].iloc[0]
            outon = trades['exit_sentiment'].iloc[-1]

            buy_and_hold_return = (self.data['close'].iloc[-1] - self.data['close'].iloc[0]) / self.data['close'].iloc[0]
            strat_over_hodl = total_return - buy_and_hold_return
            return {
                'Return': total_return,
                'Trades': num_trades,
                'Profit': win_rate,
                'StratOverHodl': strat_over_hodl,
                'inon': inon,
                'outon':outon,
            }
        # else:
            # print("No trades")

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
        # self.update_data()   #! needed for live only

        if self.data['volume'].iloc[-1] * self.data['close'].iloc[-1] < 5000:
            print(f"{self.trading_pair:10s}:Volume is too low: {int(self.data['volume'].iloc[-1]):8d} * {self.data['close'].iloc[-1]:8.2f} = {int(self.data['volume'].iloc[-1] * self.data['close'].iloc[-1]):8d}")
            exit()

        self.calculate_indicators()
        self.generate_signals()


        # test print columns
        # selected_data = self.data[['negotiation_condition','limitation_condition','contribution_condition']]
        # selected_data = self.data[['volatility','average_volatility','contribution_condition']]
        # print(">>>>",selected_data.to_string(index=True))

        # print(self.data['close'].rolling(window=self.lookback).std(),self.data['volatility'].rolling(window=self.lookback).mean())
        # input()


        # exit()
        # self.get_signal()
        # self.calculate_macd()
        # self.apply_sentiment_analysis()

        self.categorize_sentiment()

        # Get the latest data
        latest_data = self.data.iloc[-1].copy()

        return latest_data, self.data

    def get_signal(self):
        latest_data = self.data.iloc[-1]
        # macd_sentiment = self.calculate_macd()
        # print(">>>>",latest_data['buy_condition'],latest_data['sell_condition'])
        # input()

        if latest_data['buy_condition']:
            return 'BUY'
        elif latest_data['sell_condition']:
            return 'SELL'
        else:
            return 'HOLD'



