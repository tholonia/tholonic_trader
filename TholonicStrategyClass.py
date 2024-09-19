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
import cimulator_lib as t
import toml
import datetime
from GlobalsClass import (
    # LastBuyDate,
    # LastSellDate,
    last_sell_date_list,
    last_buy_date_list,
    last_buy_price_list,
    positions,
    trades_list,
    trade_counter,
    cum_return_pct,
    cum_overhodl,
    running_trx_return_pct,
    running_trx_overhodl_pct,
    capital
)


# last_buy_date = LastBuyDate()
# last_sell_date = LastSellDate()

class TholonicStrategy:
    def __init__(self, ohlc_data=None, sentiment=None, **kwargs):
        self.sentiment = sentiment
        self.configfile = kwargs.get('configfile',"cfg/cimulator.toml")
        global trades_list
        # self.trades_list = trades_list
        # Load configuration from TOML file
        with open(self.configfile, 'r') as config_file: config = toml.load(config_file)

        # override parameters from kwargs, else, use config values
        self.trading_pair           = kwargs.get('trading_pair',          config['datamanager']['trading_pair'])
        self.lookback_period        = kwargs.get('lookback_period',       config['datamanager']['window_size'])
        self.livemode               = kwargs.get('livemode',              config['datamanager']['livemode'])
        self.negotiation_threshold  = kwargs.get('negotiation_threshold', config['cfg']['negRange'][0])
        self.limitation_multiplier  = kwargs.get('limitation_multiplier', config['cfg']['limRange'][0])
        self.contribution_threshold = kwargs.get('contribution_threshold',config['cfg']['conRange'][0])
        self.stop_loss_percentage   = kwargs.get('stop_loss_percentage',  config['cfg']['stop_loss_percentage'])
        self.commission_rate        = kwargs.get('commission_rate',       config['cfg']['commission_rate'])
        self.capital                = kwargs.get('capital',              config['cfg']['initial_capital'])
        self.data = pd.DataFrame(ohlc_data)


        # Define columns and their data types
        # columns_and_dtypes = {
        #     'entry_date': 'datetime64[ns]',
        #     'entry_price': 'float64',
        #     'entry_sentiment': 'float64',
        #     'exit_date': 'datetime64[ns]',
        #     'exit_price': 'float64',
        #     'exit_sentiment': 1,
        #     'trx_return': 'float64',
        #     'buy_and_hold_return': 'float64',
        #     'trx_overhodl': 'float64',
        #     'cum_return': 'float64',
        #     'cum_overhodl': 'float64',
        # }
        columns_and_dtypes = {
            'entry_date': 'datetime64[ns]',
            'entry_price': 'float64',
            'entry_sentiment': 'int64',
            'exit_date': 'datetime64[ns]',
            'exit_price': 'float64',
            'exit_sentiment': 'int64',
            'trx_return': 'float64',
            'buy_and_hold_return': 'float64',
            'trx_overhodl': 'float64',
            'cum_return': 'float64',
            'cum_overhodl': 'float64',

        }


        # Initialize self.trades with specified columns and dtypes
        self.trades = pd.DataFrame({col: pd.Series(dtype=dt) for col, dt in columns_and_dtypes.items()})


        positions=0

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

    def dates_differ(self,entry):
        if 'entry_date' not in entry or 'exit_date' not in entry:
            return True  # Keep entries with missing dates
        return entry['entry_date'] != entry['exit_date']




    def backtest(self,sentiment_metadata_ary):
        global positions
        global last_buy_date_list
        global last_sell_date_list
        global last_buy_price_list
        global trades_list
        global trade_counter
        global cum_return_pct
        global cum_overhodl
        global running_trx_return_pct
        global running_trx_overhodl_pct
        # global capital



        # Get the last index from the data
        first_i = self.data.index[0]
        first_row = self.data.loc[first_i]
        # Get last row
        last_i = self.data.index[-1]
        last_row = self.data.loc[last_i]

        first_close  = first_row['close']
        # ttime        = last_row['time'].to_pydatetime() #???
        sentiment    = last_row['sentiment']
        last_close   = last_row['close']
        isBuy        = last_row['buy_condition']
        isSell       = last_row['sell_condition']

        # Determine whether to execute a buy order

        #! this just makes it 4x worse :/
        # # if last volatility was extreme, could be sign of a dump, so take a break
        # dump_alert_wait = 0
        # if sentiment_metadata_ary['volatility'] >= 0.07:
        #     print(bg.RED+fg.LIGHTYELLOW_EX+"DUMP ALERT"+fg.RESET+bg.RESET)
        #     if dump_alert_wait < 1: dump_alert_wait = 5
        #     else: dump_alert_wait -= 1

        #!┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
        #!┃ Test for BUY                                                            ┃
        #!┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

        doBuy = (True
            and positions == 0 # no pyramiding allowed
            and isBuy
            and last_i > last_sell_date_list[-1] # make sure this is a buy after a sell
            and last_i > last_buy_date_list[-1] # make sure this is a new buy
            # and dump_alert_wait < 1
        )

        #!━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if doBuy:
            positions += 1

            # storethe entire buy/sell tranactions in an array, and store that array in a list
            trade_entry = {
                'entry_date': last_i,  #! <class 'pandas._libs.tslibs.timestamps.Timestamp'>
                'entry_price': last_close,
                'entry_sentiment': sentiment,
            }

            trades_list.append(trade_entry)
            last_buy_date_list.append(last_i) # keep a record of the date of the last buy date
            last_buy_price_list.append(last_close) # keep a record of the price of the last buy_price

            str_entry_price = f"${trades_list[-1]['entry_price']:7.2f}"
            print(f"{last_i} "+fg.RED+f"BUY @ {str_entry_price}"+fg.RESET, end=" ")

        #~┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
        #~┃ Test for SELL                                                           ┃
        #~┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
        # Determine whether to execute a sell order
        doSell = (True
            and len(trades_list) > 0
            and positions == 1
            and isSell
            and last_close != last_buy_price_list[-1]
            # and last_i > last_buy_date_list[-1] # Ensures sell does not occur on the same timestamp as the last buy
        )
        # t.xprint("zd",trades_list)
        # print(trades_list)
        if len(trades_list) == 0:
            return {'strategy': self, 'trade_counter': trade_counter, 'positions': positions, 'capital': self.capital}

        entry_price = trades_list[-1]['entry_price']

        trx_return_pct =  (last_close - entry_price) / entry_price
        # first check the stop-loss, and if it's triggered, sell at stop-loss price
        if (True
            and positions == 1
            and trx_return_pct < -(self.stop_loss_percentage/100)
            ):
                last_close = last_buy_price_list[-1] * (1 - self.stop_loss_percentage/100)
                doSell = True
                print(bg.RED+fg.LIGHTYELLOW_EX+"STOP LOSS"+fg.RESET+bg.RESET)
        #~━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if doSell:
            positions = 0

            # make performance calculations

            buy_and_hold_return_pct =   (last_close - first_close) / first_close
            trx_overhodl_pct = trx_return_pct - buy_and_hold_return_pct
            cum_return_pct   +=  trx_return_pct
            cum_overhodl +=  trx_overhodl_pct

            # Record the sell order
            trade_exit = {
                'exit_date': last_i, #! <class 'pandas._libs.tslibs.timestamps.Timestamp'>
                'exit_price': last_close,
                'exit_sentiment': sentiment,
                'buy_and_hold_return': buy_and_hold_return_pct,
                'trx_return':  trx_return_pct * (1-self.commission_rate),
                'trx_overhodl': trx_overhodl_pct,
                'cum_return': cum_return_pct,
                'cum_overhodl': cum_overhodl
            }

            # update dict in list
            trade_counter += 1
            last_sell_date_list.append(last_i)
            trades_list[-1].update(trade_exit)



            def clrindicate(str):
                if '-' in str:
                    return bg.RED+fg.BLACK+str+fg.RESET+bg.RESET
                else:
                    return fg.GREEN+str+fg.RESET
            # BUY Sell Price
            sell_price = clrindicate(f"${trades_list[-1]['exit_price']:07.2f}")
            # Percent of transaction gain on last buy/sell cycles
            trx_gain_in_pct = clrindicate(f"${trades_list[-1]['trx_return']*100:+07.2f}%")
            # Percent of transaction gain againt boy-and-hodl
            hodl_gain_in_pct = clrindicate(f"{trades_list[-1]['trx_overhodl']*100:+3.3f}%")

            # # Cummulative tranaction gain in percentages
            running_trx_return_pct.append(trx_return_pct)
            rtrsum = sum(running_trx_return_pct)
            cumm_transaction_gain_in_pct = clrindicate(f"${rtrsum*100:7.2f}%")

            running_trx_overhodl_pct.append(trx_overhodl_pct)
            rtosum = sum(running_trx_overhodl_pct)
            cumm_transaction_overhodl_in_pct = clrindicate(f"{rtosum*100:7.2f}%")



            self.capital = self.capital * (1 + trades_list[-1]['trx_return'])
            new_capital = clrindicate(f"${self.capital:10.2f}")

            # {trades_list[-1]['trx_overhodl']*100:+3.2f}%"+fg.RESET)

            pstr = fg.GREEN
            pstr += f" {fg.WHITE}{last_sell_date_list[-1]}{fg.RESET}"
            pstr += " SEL "
            pstr += f" {sell_price:>10s}"
            pstr += f" {trx_gain_in_pct:>10s}"
            pstr += f" {hodl_gain_in_pct:>10s}"
            pstr += f" {cumm_transaction_gain_in_pct:>10s}"
            pstr += f" {cumm_transaction_overhodl_in_pct:>10s}"
            pstr += f" {new_capital:>10s}"
            # pstr += f" RT:{str_running_trx_return_pct}"
            # pstr += f" RO:{str_running_trx_overhodl_pct}"
            pstr += fg.RESET
            print(pstr)
            # print(fg.GREEN+f"SEL @ {trades_list[-1]['entry_price']:+3.4f} {trades_list[-1]['exit_price']:+3.4f} {trades_list[-1]['exit_price']-trades_list[-1]['entry_price']:+3.4f} {trades_list[-1]['trx_return']*100:+3.3f}%  {trades_list[-1]['trx_overhodl']*100:+3.2f}%"+fg.RESET)

            # print(f"{trades_list[-1]['entry_price']:+3.4f}  {trades_list[-1]['exit_price']}")


        # convert back the the nightmare that is dataframes
        self.trades = pd.DataFrame(trades_list)

        rsbt = {
            'strategy':     self,
            'trade_counter':trade_counter,
            'positions':    positions,
            'capital':      self.capital
        }
        return rsbt





    def show_data(self,data):
        # print(self.data.index) # useless
        print("▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇ df.head()")
        print(data.head())
        print("▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇ df.info()")
        print(data.info())
        print("▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇ df.types()")
        print(data.dtypes)
        print("▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇ df.describe()")
        print(data.describe())
        print("▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇ df.todict")
        pprint(self.data.to_dict()) #too long
        print("▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇ df")
        pprint(self.data) # INCOMPLETE
        print("▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇ df.index")
        print(self.data.index) #useless
        print("▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇ df.values")
        print(self.data.values) # unreadablke
        print("▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇ df.head()")
        print(self.data.head()) #useless
        print("▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇ df.tail()")
        print(self.data.tail()) #useless
        print("▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇ df.tail()")
        # exit()



#~┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
#~┃ Torch mods                                                              ┃
#~┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
#! ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ run_strategy_torch ━━━━━━━━━━━━━━━━━━━━━━━━━

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

        return self

    def run_strategy_torch(self):
        # Set the device to GPU if available
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Select only OHLCV columns
        ohlcv_columns = ['open', 'high', 'low', 'close', 'volume']
        ohlcv_data = self.data[ohlcv_columns].copy()

        # Convert DataFrame to PyTorch tensor and move to GPU
        data_tensor = torch.tensor(ohlcv_data.values, dtype=torch.float32, device=device)

        # Step 1: Calculate indicators (on GPU)
        data_tensor = self.calculate_indicators_torch(data_tensor)

        # Step 2: Generate buy/sell signals based on the indicators
        data_tensor = self.generate_signals_torch(data_tensor)

        # Step 3: Analyze sentiment using a PyTorch-based sentiment analyzer
        sentiment_analyzer = OHLCSentimentAnalyzer()
        sentiment_tensor = sentiment_analyzer.analyze_torch(data_tensor)

        # Check the dimension of sentiment_tensor and adjust if necessary
        if sentiment_tensor.dim() == 0:  # It's a scalar
            sentiment_tensor = sentiment_tensor.unsqueeze(0)
        if sentiment_tensor.dim() == 1:  # It's a 1D tensor
            sentiment_tensor = sentiment_tensor.unsqueeze(1)

        # Ensure sentiment_tensor has the same number of rows as data_tensor
        if sentiment_tensor.shape[0] != data_tensor.shape[0]:
            sentiment_tensor = sentiment_tensor.expand(data_tensor.shape[0], -1)

        # Step 4: Concatenate sentiment tensor with data_tensor
        data_tensor = torch.cat([data_tensor, sentiment_tensor], dim=1)


        # Step 5: Create column names for the tensor
        columns = ohlcv_columns + [
            'price_change', 'average_volume', 'volatility', 'average_volatility',
            'negotiation_condition', 'limitation_condition', 'contribution_condition',
            'buy_condition', 'sell_condition', 'sentiment'
        ]

        # Step 6: Convert boolean columns
        bool_columns = ['negotiation_condition', 'limitation_condition', 'contribution_condition', 'buy_condition', 'sell_condition']
        bool_indices = [columns.index(col) for col in bool_columns]
        data_tensor[:, bool_indices] = torch.round(torch.sigmoid(data_tensor[:, bool_indices]))

        # Step 7: Move results back to CPU and convert to numpy
        cpu_data = data_tensor.cpu().numpy()

        # Step 8: Create a new DataFrame with all columns
        self.data = pd.DataFrame(cpu_data, columns=columns, index=self.data.index)

        # Convert boolean columns to proper boolean type
        self.data[bool_columns] = self.data[bool_columns].astype(bool)

        # Step 9: Return the latest row of data and the updated DataFrame
        latest_data = torch.tensor(self.data.iloc[-1].values, dtype=torch.float32, device=device)

        return latest_data, self.data






    def cc_run_strategy_torch(self):
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

#! ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ calculate_indicators ━━━━━━━━━━━━━━━━━━━━━━━━━

    def calculate_indicators(self):
        # Price change remains the same as it's calculated per row (old comment, but I have no idea what I was referring to :/ )
        self.data['price_change'] = (self.data['close'] - self.data['open']) / self.data['open'] * 100

        # Use the mean of all volume data in the set
        self.data['average_volume'] = self.data['volume'].mean()

        # Calculate volatility as the standard deviation of all close prices in the set
        self.calculate_volatility(volatility_method='parkinsons')


    def calculate_indicators_torch(self, data_tensor):
        open_price, high, low, close, volume = data_tensor.unbind(1)

        price_change = (close - open_price) / open_price * 100
        average_volume = volume.mean().expand_as(volume)
        volatility = torch.abs(high - low) / close * 100

        # Ensure average_volatility has the same size as other tensors
        padding = (self.lookback_period - 1) // 2
        average_volatility = F.avg_pool1d(volatility.unsqueeze(0).unsqueeze(0),
                                        kernel_size=self.lookback_period,
                                        stride=1,
                                        padding=padding).squeeze(0).squeeze(0)

        # Ensure all tensors have the same size
        min_length = min(len(data_tensor), len(price_change), len(average_volume), len(volatility), len(average_volatility))
        data_tensor = data_tensor[-min_length:]
        price_change = price_change[-min_length:]
        average_volume = average_volume[-min_length:]
        volatility = volatility[-min_length:]
        average_volatility = average_volatility[-min_length:]

        return torch.cat([data_tensor,
                        price_change.unsqueeze(1),
                        average_volume.unsqueeze(1),
                        volatility.unsqueeze(1),
                        average_volatility.unsqueeze(1)], dim=1)

    # def calculate_indicators_torch(self, data_tensor):
    #     # Unpack columns (assuming the first 5 columns are: open_price, high, low, close, volume)
    #     open_price, high, low, close, volume = data_tensor.unbind(1)

    #     # Step 1: Calculate price change as a percentage
    #     price_change = (close - open_price) / open_price * 100
    #     data_tensor = torch.cat([data_tensor, price_change.unsqueeze(1)], dim=1)

    #     # Step 2: Calculate average volume
    #     avg_volume = volume.mean().expand(volume.shape[0], 1)  # Mean volume across all entries
    #     data_tensor = torch.cat([data_tensor, avg_volume], dim=1)

    #     # Step 3: Calculate volatility using Garman-Klass method
    #     log_hl = torch.log(high / low).pow(2)
    #     log_co = torch.log(close / open_price).pow(2)
    #     volatility = torch.sqrt(0.5 * log_hl - (2 * torch.log(torch.tensor(2.0, device=data_tensor.device)) - 1) * log_co)

    #     # Step 4: Apply annualization factor for volatility (e.g., assuming 8760 hours in a year)
    #     annualization_factor = torch.sqrt(torch.tensor(8760.0, device=data_tensor.device))
    #     volatility *= annualization_factor
    #     data_tensor = torch.cat([data_tensor, volatility.unsqueeze(1)], dim=1)

    #     # Step 5: Calculate average volatility using a cumulative sum
    #     cumsum_volatility = torch.cumsum(volatility, dim=0)  # Cumulative sum of volatility
    #     # Create a lookback tensor, clamped by self.lookback, for moving average calculations
    #     lookback_tensor = torch.arange(1, len(volatility) + 1, device=data_tensor.device).float().clamp(max=self.lookback_period)
    #     avg_volatility = cumsum_volatility / lookback_tensor  # Rolling average of volatility
    #     data_tensor = torch.cat([data_tensor, avg_volatility.unsqueeze(1)], dim=1)

    #     return data_tensor

    def cc_calculate_indicators_torch(self, data_tensor):
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

#! ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ generate_signals ━━━━━━━━━━━━━━━━━━━━━━━━━

    def generate_signals(self):
        self.data['negotiation_condition'] = self.data['price_change'] >= self.negotiation_threshold
        self.data['limitation_condition'] = self.data['volume'] >= self.data['average_volume'] * self.limitation_multiplier
        self.data['contribution_condition'] = self.data['volatility'] <= self.data['average_volatility'] * self.contribution_threshold


        # t.xprint("neg",self.data['negotiation_condition'].iloc[-1],co=fg.LIGHTRED_EX, ex=False)
        # t.xprint("lim",self.data['limitation_condition'].iloc[-1],co=fg.LIGHTGREEN_EX, ex=False)
        # t.xprint("con",self.data['contribution_condition'].iloc[-1],co=fg.LIGHTBLUE_EX, ex=False)

        self.data['buy_condition'] = (
            self.data['negotiation_condition'] &
            self.data['limitation_condition'] &
            self.data['contribution_condition']
        )
        # t.xprint("neg",self.data['buy_condition'].iloc[-1],co=fg.LIGHTRED_EX, ex=False)

        self.data['sell_condition'] = (
            (self.data['volatility'] < self.data['average_volatility']) &
            (self.data['volatility'].shift(1) >= self.data['average_volatility'].shift(1))
        )

        #reassign self.data['volatility'] to be True/False
        self.data['volatility'] = self.data['volatility'] <= self.data['average_volatility'] * self.contribution_threshold

    def cc_generate_signals_torch(self, data_tensor):
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


    def generate_signals_torch(self, data_tensor):
        # Implement your signal generation logic here using PyTorch operations
        # This is a placeholder implementation
        price_change, average_volume, volatility, average_volatility = data_tensor[:, -4:].unbind(1)

        negotiation_condition = price_change >= self.negotiation_threshold
        limitation_condition = data_tensor[:, 4] >= average_volume * self.limitation_multiplier
        contribution_condition = volatility <= average_volatility * self.contribution_threshold

        buy_condition = negotiation_condition & limitation_condition & contribution_condition
        sell_condition = volatility < average_volatility

        signals = torch.stack([negotiation_condition, limitation_condition, contribution_condition,
                            buy_condition, sell_condition], dim=1).float()

        return torch.cat([data_tensor, signals], dim=1)

    # def generate_signals_torch(self, data_tensor):
    #     # Unpack necessary columns from the tensor
    #     price_change, volume, average_volume, volatility, average_volatility = data_tensor[:, -5:].unbind(1)

    #     # Step 1: Calculate negotiation condition (price_change >= negotiation_threshold)
    #     negotiation_condition = price_change >= self.negotiation_threshold

    #     # Step 2: Calculate limitation condition (volume >= average_volume * limitation_multiplier)
    #     limitation_condition = volume >= average_volume * self.limitation_multiplier

    #     # Step 3: Calculate contribution condition (volatility <= average_volatility * contribution_threshold)
    #     contribution_condition = volatility <= average_volatility * self.contribution_threshold

    #     # Step 4: Calculate buy condition (negotiation & limitation & contribution)
    #     buy_condition = negotiation_condition & limitation_condition & contribution_condition

    #     # Step 5: Calculate sell condition (volatility < average_volatility) & (previous volatility >= previous average_volatility)
    #     prev_volatility = torch.roll(volatility, shifts=1)  # Shift volatility by 1 to get the previous value
    #     prev_avg_volatility = torch.roll(average_volatility, shifts=1)
    #     sell_condition = (volatility < average_volatility) & (prev_volatility >= prev_avg_volatility)

    #     # Step 6: Reassign volatility column (True/False) based on whether volatility <= average_volatility * contribution_threshold
    #     volatility_condition = volatility <= average_volatility * self.contribution_threshold

    #     # Step 7: Concatenate the conditions back to the data tensor
    #     # Adding negotiation, limitation, contribution, buy, sell, and volatility_condition as new columns
    #     conditions_tensor = torch.stack([
    #         negotiation_condition, limitation_condition, contribution_condition,
    #         buy_condition, sell_condition, volatility_condition
    #     ], dim=1).float()

    #     # Concatenate new conditions to the original data_tensor
    #     data_tensor = torch.cat([data_tensor, conditions_tensor], dim=1)

    #     return data_tensor
