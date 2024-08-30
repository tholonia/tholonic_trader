#!/usr/bin/env python
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import sqlite3
import os
import hashlib
import time
import ccxt
# from trade_bot_lib import DatabaseManager, TholonicStrategy
from colorama import Fore as fg, Back as bg, Style as st
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.widgets import MultiCursor
import matplotlib.ticker as ticker
import matplotlib
matplotlib.use('TkAgg')
import getopt
from datetime import datetime
import re
import traceback


def report_time(name,starttime,endtime):
    pass


class DataLoader:
    def __init__(self, ohlcfile, from_date, to_date, livemode_n_elements=None):
        # Read the CSV file
        self.data = pd.read_csv(ohlcfile)

        # Convert the 'timestamp' column to datetime
        self.data['timestamp'] = pd.to_datetime(self.data['timestamp'])

        # Set 'timestamp' as the index
        self.data.set_index('timestamp', inplace=True)

        # Filter the data based on the date range
        self.data = self.data.loc[from_date:to_date]

        # If livemode_n_elements is specified, limit the number of rows
        if livemode_n_elements is not None:
            self.data = self.data.head(livemode_n_elements)

        # Get the last record
        self.last_record = self.data.iloc[-1] if not self.data.empty else None

        # report_time("Dataloader::__init__",starttime,time.time())

    def get_data(self):
        return self.data

    def get_last_record(self):
        return self.last_record


class TholonicStrategy:
    def __init__(self, trading_pair, negotiation_threshold, limitation_multiplier,
                 contribution_threshold, lookback_period, livemode, livemode_n_elements,
                 ohlcfile, from_date, to_date):
        # starttime = time.time()
        # Strategy parameters
        self.trading_pair = trading_pair
        self.lookback = lookback_period
        self.negotiation_threshold = negotiation_threshold
        self.limitation_multiplier = limitation_multiplier
        self.contribution_threshold = contribution_threshold
        self.livemode = livemode
        self.livemode_n_elements = livemode_n_elements

        if not self.livemode:
            try:
                loader = DataLoader(ohlcfile, from_date, to_date, self.livemode_n_elements)
                self.data = loader.get_data()
            except ValueError as e:
                print(f"Error loading data: {e}")
                sys.exit(1)
        else:
            self.data = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
            self.data.index.name = 'timestamp'

        # Initialize exchange
        if livemode:
            self.exchange = ccxt.kraken({
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future'
                }
            })
        # report_time("TholonicStrategy::__init__",starttime,time.time())

    def fetch_ohlcv(self, symbol, timeframe, limit):
        # starttime = time.time()
        ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        # report_time("TholonicStrategy::fetch_ohlcv",starttime,time.time())
        return df

    def update_data(self):
        if self.livemode:
            new_data = self.fetch_ohlcv(self.trading_pair, '1m', limit=self.lookback)
            if self.data.empty:
                self.data = new_data
            else:
                self.data = pd.concat([self.data, new_data]).drop_duplicates().sort_index().tail(self.lookback)

    def calculate_indicators(self):
        self.data['price_change'] = (self.data['close'] - self.data['open']) / self.data['open'] * 100
        self.data['average_volume'] = self.data['volume'].rolling(window=self.lookback).mean()
        self.data['volatility'] = self.data['close'].rolling(window=self.lookback).std()
        self.data['average_volatility'] = self.data['volatility'].rolling(window=self.lookback).mean()

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

    def run_strategy(self):
        self.update_data()
        self.calculate_indicators()
        self.generate_signals()
        return self.data.iloc[-1]

    def get_signal(self):
        latest_data = self.data.iloc[-1]
        if latest_data['buy_condition']:
            return 'BUY'
        elif latest_data['sell_condition']:
            return 'SELL'
        else:
            return 'HOLD'



def calculate_average_position_price(positions):
    if not positions:
        return 0
    total_cost = sum(price * amount for price, amount in positions)
    total_amount = sum(amount for _, amount in positions)
    return total_cost / total_amount if total_amount > 0 else 0

def calculate_profit(entry_positions, exit_price, exit_amount, commission_rate):
    avg_entry_price = calculate_average_position_price(entry_positions)
    gross_profit = (exit_price - avg_entry_price) * exit_amount

    # Calculate commission for both entry and exit
    entry_commission = avg_entry_price * exit_amount * commission_rate
    exit_commission = exit_price * exit_amount * commission_rate

    # Subtract both entry and exit commissions from gross profit
    net_profit = gross_profit - entry_commission - exit_commission

    # Calculate net profit percentage
    total_investment = avg_entry_price * exit_amount
    net_profit_percentage = (net_profit / total_investment) * 100 if total_investment > 0 else 0

    return net_profit, net_profit_percentage

def print_trading_info(
        idx,
        timestamp,
        trading_pair,
        signal,
        close_price,
        avg_position_price,
        total_profit,
        total_profit_percentage,
        long_positions,
        num_positions,
        order_submission_status,
        total_units_held,
        transaction_profit = None,
    ):
    base_message = f"{idx:04d} Timestamp: {timestamp}, Pair: {trading_pair}, Signal: {signal}, Close Price: {close_price:.2f}, Total Units Held: {total_units_held:.6f}, Avg Position: {avg_position_price:.2f}, Total Profit: {total_profit:.2f} ({total_profit_percentage:.2f}%), Long Positions: {long_positions}, Num Positions: {num_positions}"

    if signal == "HOLD":
        pass
        # print(fg.BLUE + base_message + fg.RESET)

    elif signal == "BUY":
        _ts = f"{timestamp}"
        _tp = f"{trading_pair}"
        _cp = f"Close: ${close_price:.2f}"
        _th = f"Total Units Held: {total_units_held:.6f}"
        _ap = f"Avg Pos: ${avg_position_price}"
        _np = f"Num Pos: {num_positions}"

        base_message = f"{idx:04d} {_ts} {signal:5s}, {_tp}, {_cp}, {_th}, {_ap}, {_np}"

        if order_submission_status != "unavailable":
            print(fg.RED + base_message + fg.RESET)
        else:
            print(fg.LIGHTBLUE_EX + base_message + " unavailable" + fg.RESET)

    elif signal == "SELL":

        _ts = f"{timestamp}"
        _tp = f"{trading_pair}"
        _cp = f"Close: ${close_price:.2f}"
        _tP = f"Total Profit: {fg.MAGENTA}{total_profit:.2f}{fg.GREEN}"
        _tPp = f"{fg.MAGENTA}{total_profit_percentage:.2f}%"
        if transaction_profit <0:
            _tPt = f"{bg.RED}{fg.BLACK}{transaction_profit:.2f}%{bg.RESET}{fg.RESET}"
        else:
            _tPt = f"{fg.GREEN}{transaction_profit:.2f}%{fg.RESET}"

        base_message = f"{idx:04d} {_ts} {signal:5s}, {_tp}, {_cp}, {_tP}, {_tPp}, {_tPt}"
        print(fg.GREEN + base_message + fg.RESET+"\n")

    else:
        print(fg.WHITE + base_message + fg.RESET)

def check_stop_loss(positions, current_price, stop_loss_percentage):
    if not positions:
        return False
    avg_entry_price = calculate_average_position_price(positions)
    stop_loss_price = avg_entry_price * (1 - stop_loss_percentage)
    return current_price <= stop_loss_price

class ProfitLossPlotter:
    def __init__(self):
        self.timestamps = []
        self.profits = []
        self.cumulative_profits = []
        self.prices = []
        self.buy_points = []
        self.sell_points = []
        self.price_deltas = []
        self.sma_price_deltas = []
        self.volatilities = []
        self.average_volatilities = []

    def add_trade(self, timestamp, profit, price, trade_type=None, volatility=None, average_volatility=None, available_positions=0):

        self.timestamps.append(timestamp)
        self.profits.append(profit)
        self.prices.append(price)


        if not self.cumulative_profits:
            self.cumulative_profits.append(profit)
        else:
            self.cumulative_profits.append(self.cumulative_profits[-1] + profit)
        if trade_type == 'BUY':
            if available_positions > 0:
                    self.buy_points.append((timestamp, price))
        elif trade_type == 'SELL':
            if available_positions > 0:
                self.sell_points.append((timestamp, price))

        # Calculate price delta
        if len(self.prices) > 1:
            price_delta = (price - self.prices[-2]) / self.prices[-2] * 100
            self.price_deltas.append(price_delta)
        else:
            self.price_deltas.append(0)

        # Calculate SMA of price delta (let's use a 14-period SMA)
        if len(self.price_deltas) >= 14:
            sma = sum(self.price_deltas[-14:]) / 14
            self.sma_price_deltas.append(sma)
        else:
            self.sma_price_deltas.append(0)

        # Add volatility and average volatility
        self.volatilities.append(volatility)
        self.average_volatilities.append(average_volatility)

    def plot(self, initial_balance,negotiation_threshold, limitation_multiplier, contribution_threshold, lookback_period,volatility,verbosity,stop_loss):
        fig, axes = plt.subplots(3, 1, figsize=(23, 13), sharex=True)
        ax1, ax2, ax4 = axes  # Unpack the axes array

        dates = pd.to_datetime(self.timestamps)
        plt.rcParams.update({'font.size': 8})

        #!———————————————————————————————————————————————————————————————————————————
        # Plot individual trade profits/losses
        ax1.bar(dates, self.profits, color=['g' if p > 0 else 'r' for p in self.profits])
        ax1.set_title('Individual Trade Profits/Losses')
        ax1.set_ylabel('Profit/Loss')
        ax1.axhline(y=0, color='k', linestyle='-', linewidth=0.5)
        #!———————————————————————————————————————————————————————————————————————————
        # Plot cumulative profit and buy-and-hold value
        ax2.plot(dates, self.cumulative_profits, color='b', label='Strategy', zorder=3)

        # Calculate and plot buy-and-hold value
        initial_price = self.prices[0]
        buy_and_hold_values = [initial_balance * (price / initial_price) - initial_balance for price in self.prices]
        ax2.plot(dates, buy_and_hold_values, color='r', label='Buy and Hold', zorder=3)

        ax2.set_title('Cumulative Profit vs Buy and Hold')
        ax2.set_ylabel('Profit')
        ax2.legend()
        #!———————————————————————————————————————————————————————————————————————————
        # Add buy and sell markers
        date_to_index = {date: index for index, date in enumerate(dates)}

        buy_dates = [pd.to_datetime(date) for date, _ in self.buy_points]

        buy_indices = [date_to_index.get(date) for date in buy_dates if date in date_to_index]
        buy_values = [buy_and_hold_values[i] for i in buy_indices if i is not None]
        ax2.scatter(buy_dates, buy_values, color='darkviolet', marker='v', s=30, label='Buy', zorder=2)

        sell_dates = [pd.to_datetime(date) for date, _ in self.sell_points]
        sell_indices = [date_to_index.get(date) for date in sell_dates if date in date_to_index]
        sell_values = [buy_and_hold_values[i] for i in sell_indices if i is not None]
        ax2.scatter(sell_dates, sell_values, color='lime', marker='^', s=30, label='Sell', zorder=2)

        ax2.set_title('Cumulative Profit vs Buy and Hold')
        ax2.set_ylabel('Profit')
        ax2.legend(['Strategy', 'Buy and Hold', 'Buy', 'Sell'])
        #!———————————————————————————————————————————————————————————————————————————
        # Plot volatility and average volatility
        ax4.plot(dates, self.volatilities, color='b', label='Volatility (STD)')
        ax4.plot(dates, self.average_volatilities, color='r', label='Average Volatility')
        ax4.set_title('Volatility (STD) and Average Volatility')
        ax4.set_ylabel('Volatility')
        ax4.legend()
        #!———————————————————————————————————————————————————————————————————————————

        plt.gcf().autofmt_xdate()  # Rotate and align the tick labels
        plt.subplots_adjust(left=0.1, right=0.95, bottom=0.1, top=0.95)

        # Format the date axis to show monthly labels and daily ticks without numbers
        for ax in axes:
            # Set major ticks and labels for each month
            ax.xaxis.set_major_locator(mdates.MonthLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))

            # Set minor ticks for each day (without labels)
            ax.xaxis.set_minor_locator(mdates.DayLocator())

            # Customize the appearance of the ticks
            ax.tick_params(axis='x', which='major', rotation=45, labelsize=8, pad=15)
            ax.tick_params(axis='x', which='minor', length=4, width=0.5, labelsize=0)  # Set labelsize to 0 to hide minor tick labels
            ax.tick_params(axis='y', labelsize=8)

            # Draw the grid for each day
            ax.grid(which='minor', axis='x', linestyle=':', linewidth=0.5, alpha=0.7)
            ax.grid(which='major', axis='x', linestyle='-', linewidth=0.8, alpha=0.9)



        # Adjust the layout
        plt.tight_layout()

        # Add MultiCursor
        multi = MultiCursor(fig.canvas, (ax1, ax2, ax4), color='r', lw=1, horizOn=True, vertOn=True)

        # plot_name = f"n{negotiation_threshold}l{limitation_multiplier}c{contribution_threshold}k{lookback_period}v{volatility}s{stop_loss}.png"
        plot_name = f"n{negotiation_threshold}l{limitation_multiplier}c{contribution_threshold}k{lookback_period}s{stop_loss}.png"

        plt.savefig(plot_name, dpi=100, bbox_inches='tight')

        if verbosity != 101:
            plt.show()
        plt.close()


def extract_date_range_from_special_csv(file_path, date_format='%Y-%m-%d %H:%M:%S'):
    """
    Extracts the first and last dates from a CSV file with a header row and data rows where values are not comma-separated.
    In these files the timestamp is in a string format, ex "2024-12-01 00:00:00"

    :param file_path: Path to the CSV file
    :param date_format: Format of the date string in the CSV (default is '%Y-%m-%d %H:%M:%S')
    :return: A tuple containing the first and last dates as strings, or (None, None) if no valid dates are found
    """
    try:
        with open(file_path, 'r') as file:
            # Skip the header row
            next(file)

            # Read the first data line
            first_line = next(file).strip()

            # Read the last data line
            for last_line in file:
                pass
            last_line = last_line.strip()

        # Extract the date strings using regex
        date_pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'
        first_date_match = re.search(date_pattern, first_line)
        last_date_match = re.search(date_pattern, last_line)

        if first_date_match and last_date_match:
            first_date_str = first_date_match.group(1)
            last_date_str = last_date_match.group(1)

            # Parse and format the dates
            first_date = datetime.strptime(first_date_str, date_format).strftime('%Y-%m-%d')
            last_date = datetime.strptime(last_date_str, date_format).strftime('%Y-%m-%d')

            return first_date, last_date
        else:
            raise ValueError("Could not find date strings in the expected format")

    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()
        return None, None


def print_usage():
    str = """
    Usage: python trading_strategy_tool.py [options]")
    Options:")
      -h, --help                    Show this help message and exit
      -p, --pair=PAIR               Trading pair (*BTCUSD)
      -b, --livemode                Run in livemode mode (*backtest mode)
      -m, --max-positions=MAX       Maximum number of positions (*3)
      -n, --negotiation=THRESHOLD   Negotiation threshold (*0.2)
      -l, --limitation=MULTIPLIER   Limitation multiplier (*0.2)
      -c, --contribution=THRESHOLD  Contribution threshold (*1.8)
      -k, --lookback=PERIOD         Lookback period (*16)
      -r, --commission=RATE         Commission rate (*0.001 = 0.1%)
      -s, --stop-loss=PERCENTAGE    Stop loss percentage (*1%)
      -i, --initial-balance=BALANCE Initial balance for buy-and-hold comparison (*1000)
      -v, --verbosity=LEVEL         1,2,3... Verbosity level (*1)
      -R, --daterange               from|to dates ex "2022-12-13|2023-12-16"
      -F, --ohlcfile                OHLCV file (*data/BTCUSD_OHLC_1440_default.csv)
      -L, --limitcount              Limit count (*720)
      Verbosity levels:
        0: No screen output
        1: Profitability summary
        2: Profitability summary + detailed trading info
        3: Profitability summary + detailed trading info + plot

"""
    print(str)
    exit()


def main(argv):
    trading_pair = "BTCUSD"
    livemode = False
    max_positions = 2
    # ideal for 1h candles
    negotiation_threshold = 1.0
    limitation_multiplier = 1.5
    contribution_threshold = 1.2
    lookback_period = 16

    commission_rate = 0.001 # 0.1%
    stop_loss_percentage = 1 # 1%
    initial_balance = 1000
    verbosity_level = 0
    limitcount = 720
    ohlcfile = "data//BTCUSD_OHLC_1440_default.csv"
    from_date = "2016-12-10"
    to_date = "2017-12-16"


    total_units_held = 0

    try:
        opts, args = getopt.getopt(argv, "hp:bm:n:l:c:k:r:s:i:v:L:F:R:",
                                   ["help", "pair=", "livemode", "max-positions=", "negotiation=",
                                    "limitation=", "contribution=", "lookback=", "commission=",
                                    "stop-loss=", "initial-balance=", "verbosity=","limitcount=","ohlcfile=","daterange="])
    except getopt.GetoptError:
        print_usage()
        sys.exit(2)

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print_usage()
            sys.exit()
        elif opt in ("-p", "--pair"):
            trading_pair = arg
        elif opt in ("-b", "--livemode"):
            livemode = True
        elif opt in ("-m", "--max-positions"):
            max_positions = int(arg)
        elif opt in ("-n", "--negotiation"):
            negotiation_threshold = float(arg)
        elif opt in ("-l", "--limitation"):
            limitation_multiplier = float(arg)
        elif opt in ("-c", "--contribution"):
            contribution_threshold = float(arg)
        elif opt in ("-k", "--lookback"):
            lookback_period = int(arg)
        elif opt in ("-r", "--commission"):
            commission_rate = float(arg)
        elif opt in ("-s", "--stop-loss"):
            stop_loss_percentage = float(arg)/100
        elif opt in ("-i", "--initial-balance"):
            initial_balance = float(arg)
        elif opt in ("-v", "--verbosity"):
            verbosity_level = int(arg)
        elif opt in ("-L", "--limitcount"):
            limitcount = int(arg)
        elif opt in ("-F", "--ohlcfile"):
            ohlcfile = arg
        elif opt in ("-R", "--daterange"):
            from_date, to_date = arg.split("|")
            if len(from_date) < 11:
                from_date = from_date + " 00:00:00"
            if len(to_date) < 11:
                if to_date == "now":
                    to_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                else:
                    to_date = to_date + " 00:00:00"

    # print(f"from_date: {from_date} to_date: {to_date}")
    livemode_idx_iter = 0
    previous_time = ""

    # Position tracking
    current_positions = []
    total_profit = 0
    total_profit_percentage = 0
    long_positions = False
    num_positions = 0

    first_purchase_price = None
    final_selling_price = 0

    # thus uses the entire file by default
#    from_date, to_date = extract_date_range_from_special_csv(ohlcfile)

    # Profitability tracking
    profitable_trades = 0
    non_profitable_trades = 0

    # Buy-and-hold tracking
    initial_price = None
    avg_position_price = None

    # Initialize the profit/loss plotter
    plotter = ProfitLossPlotter()


    # Initialize current_capital to None, we'll set it on the first purchase
    current_capital = None

    from_date_dt = datetime.strptime(from_date, "%Y-%m-%d %H:%M:%S")
    to_date_dt = datetime.strptime(to_date, "%Y-%m-%d %H:%M:%S")

    # starttime = time.time()
    while True:
        order_submission_status = ""
        try:
            strategy = TholonicStrategy(
                trading_pair=trading_pair,
                negotiation_threshold=negotiation_threshold,
                limitation_multiplier=limitation_multiplier,
                contribution_threshold=contribution_threshold,
                lookback_period=lookback_period,
                livemode=livemode,
                livemode_n_elements=livemode_idx_iter+lookback_period,
                ohlcfile=ohlcfile,
                from_date=from_date,
                to_date=to_date,
            )
            latest_data = strategy.run_strategy()
            livemode_idx_iter += 1
            signal = strategy.get_signal()
            current_time = f"{latest_data.name}"  # CONVER TO STR
            current_time_dt = datetime.strptime(current_time, "%Y-%m-%d %H:%M:%S")
            current_price = latest_data['close']
            in_date_range = from_date_dt <= current_time_dt <= to_date_dt
            available_positions = max_positions - len(current_positions)

            # stop signal
            if current_time_dt > to_date_dt:
                break

            # Break when we get to the end of the data (for livemodeing)
            if current_time == previous_time:# or livemode_idx_iter > limitcount:
                break
            previous_time = current_time

            # Check for stop loss
            if check_stop_loss(current_positions, current_price, stop_loss_percentage):
                signal = "SELL"
                if verbosity_level > 1 and verbosity_level < 100:
                    print(fg.LIGHTYELLOW_EX + f"Stop loss ({stop_loss_percentage*100:.2f}%) triggered at {current_price:.2f}" + fg.RESET)

            # Position management
            if signal == "BUY":
                if available_positions > 0 and in_date_range: #! and latest_data['volatility'] < 1000:
                    if initial_price is None:
                        initial_price = current_price

                    if first_purchase_price is None:
                        first_purchase_price = current_price
                        current_capital = first_purchase_price

                    # Calculate the investment amount for this position
                    # Divide the current capital by the remaining available positions
                    # This ensures equal distribution of capital across all potential positions
                    investment_amount = current_capital / (max_positions - num_positions)

                    # Calculate the number of units to buy based on the investment amount and current price
                    units_to_buy = investment_amount / current_price

                    # Append the current price and the calculated units to the current positions list
                    current_positions.append((current_price, units_to_buy))

                    # Add the units to the total units held
                    total_units_held += units_to_buy

                    # Set the long_positions flag to True
                    long_positions = True

                    # Calculate the average position price
                    avg_position_price = calculate_average_position_price(current_positions)

                    # Add to "Individual Trade Porfits/Losses" to the plotter
                    plotter.add_trade(current_time, 0, current_price, 'BUY', available_positions = available_positions)

                    if verbosity_level > 1 and verbosity_level < 100:
                        print_trading_info(
                            livemode_idx_iter,
                            current_time,
                            trading_pair,
                            signal,
                            current_price,
                            avg_position_price,
                            total_profit,
                            total_profit_percentage,
                            long_positions,
                            num_positions,
                            order_submission_status,
                            total_units_held,
                        )
                else:
                    order_submission_status = "unavailable"

            # Handling the SELL signal when there are open positions
            elif signal == "SELL" and current_positions and in_date_range: #! and latest_data['volatility'] >= 1000: # and total_units_held > 0:

                volatility = latest_data['volatility']
                average_volatility = latest_data['average_volatility']

                # Calculate the profit for closing all positions at the current price, including commission
                total_amount = sum(amount for _, amount in current_positions)
                profit, profit_percentage = calculate_profit(current_positions, current_price, total_amount, commission_rate)
                total_units_held = 0

                # Update profitability tracking
                if profit > 0:
                    profitable_trades += 1
                else:
                    non_profitable_trades += 1

                # Add the calculated profit to the total profit
                total_profit += profit
                total_profit_percentage += profit_percentage
                transaction_profit = ((current_price-avg_position_price)/avg_position_price)*100

                # Update the current capital
                current_capital += profit

                # Close all positions by resetting the current_positions list
                current_positions = []
                # Update flags to indicate no open positions
                long_positions = False
                # num_positions = 0
                available_positions = max_positions
                final_selling_price = current_price


                # Add to "Individual Trade Porfits/Losses" to the plotter
                #! adding SELL to the add_trade MUST come after calculating available_positions because it uses that to know how
                #! many positions were open!

                plotter.add_trade(current_time, profit, current_price, 'SELL',available_positions=available_positions)

                if verbosity_level > 1 and verbosity_level < 100:
                    print_trading_info(
                        livemode_idx_iter,
                        current_time,
                        trading_pair,
                        signal,
                        current_price,
                        0,  # avg_position_price is 0 after selling
                        total_profit,
                        total_profit_percentage,
                        long_positions,
                        num_positions,
                        order_submission_status,
                        total_units_held,
                        transaction_profit,
                    )
                    # print(fg.YELLOW + f"Total units held after sell: {total_units_held:.6f}" + fg.RESET)
                else:
                    pass
            else:
                pass

            # If we've made at least one purchase, update the plotter with the latest data
            if first_purchase_price is not None:
                volatility = latest_data['volatility']
                average_volatility = latest_data['average_volatility']
                # Add the current trade data to the plotter
                # Adds ALL closes to the price line (buy and hold line)
                plotter.add_trade(current_time, 0, current_price, signal, volatility, average_volatility)

            time.sleep(0.0)  # Wait before next update
        except KeyboardInterrupt:
            print("Strategy stopped by user.")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()
            print("Wait for 1 minute before retrying")
            time.sleep(60)

    # Calculate and print profitability ratio
    total_trades = profitable_trades + non_profitable_trades
    if total_trades > 0:
        profit_ratio = profitable_trades / total_trades
        buy_and_hold_return = (final_selling_price - initial_price) / initial_price * 100

        if verbosity_level > 0 and verbosity_level < 100:
            str = f"""
{fg.CYAN}
Profitability Summary:          n:{negotiation_threshold} l:{limitation_multiplier} c:{contribution_threshold} k:{lookback_period} s:{stop_loss_percentage}{fg.RESET}
Date Range:                     {from_date} - {to_date}
TT: Total Trades:               {total_trades}
PT: Profitable Trades:          {profitable_trades}
PN: Non-Profitable Trades:      {non_profitable_trades}
PR: Profit Ratio:               {profit_ratio:.2%}

IC: Initial Capital (1st buy): ${first_purchase_price:.2f}
FS: Final Selling Price:       ${final_selling_price:.2f}
TP: Total Profit:              ${total_profit:.2f} ({total_profit_percentage:.2f}%)
BH: Buy-and-Hold Return:        {buy_and_hold_return:.2f}%

FC: Final Capital:             ${current_capital:.2f}
TR: Total Return:               {(current_capital - first_purchase_price) / first_purchase_price * 100:.2f}%
TH: Total Units Held at End:    {total_units_held:.6f}
"""
            print(str)
            # Calculate buy-and-hold return
        if verbosity_level == 101:
            str = f"n:{fg.LIGHTBLUE_EX}{negotiation_threshold:1.2f}{fg.RESET}"
            str += F"l:{fg.LIGHTCYAN_EX}{limitation_multiplier:1.2f}{fg.RESET}"
            str += f"c:{fg.LIGHTMAGENTA_EX}{contribution_threshold:1.2f}{fg.RESET}"
            str += f"k:{fg.LIGHTGREEN_EX}{lookback_period:02d}{fg.RESET}"
            str += f"s:{fg.LIGHTBLUE_EX}{stop_loss_percentage*100:.2f}{fg.RESET}"
            str += f"|{from_date} - {to_date}"
            str += f"|TT: {fg.CYAN}{total_trades:4d}{fg.RESET}"
            str += f"|PN: {fg.YELLOW}{profitable_trades:3d}/{non_profitable_trades:3d}{fg.RESET}"
            str += f"|PR: {fg.GREEN}{profit_ratio:.2%}{fg.RESET}"
            str += f"|TP: {fg.RED}${total_profit:8.2f} ({total_profit_percentage:6.2f}%){fg.RESET}"
            str += f"|FC: {fg.LIGHTCYAN_EX}${current_capital:8.2f}{fg.RESET}"
            str += f"|TR: {fg.LIGHTYELLOW_EX}${(current_capital - first_purchase_price) / first_purchase_price * 100:6.2f}%{fg.RESET}"  #TODO replace focumla with buy_and_hold return, if theyt are teh same
            str += f"|FL: {fg.LIGHTMAGENTA_EX}${first_purchase_price:8.2f}/{final_selling_price:8.2f}{fg.RESET}"
            str += f"|TH: {fg.LIGHTGREEN_EX}{total_units_held:8.6f}{fg.RESET}"
            print(str)

    else:
        print(fg.CYAN + f"\nNo trades were executed during the livemode." + fg.RESET)



    # Plot the profits and losses
    if (verbosity_level > 2 and verbosity_level < 100) or verbosity_level == 101:
        plotter.plot(
            first_purchase_price,
            negotiation_threshold,
            limitation_multiplier,
            contribution_threshold,
            lookback_period,
            volatility,
            verbosity_level,
            stop_loss_percentage,
        )

if __name__ == "__main__":
    main(sys.argv[1:])





