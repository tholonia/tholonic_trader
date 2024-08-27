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
import matplotlib
matplotlib.use('TkAgg')

class TholonicStrategy:
    def __init__(self, trading_pair, negotiation_threshold, limitation_multiplier,
                 contribution_threshold, lookback_period,backtest,backtest_n_elements):

       # Strategy parameters
        self.trading_pair = trading_pair
        self.lookback = lookback_period
        self.negotiation_threshold = negotiation_threshold
        self.limitation_multiplier = limitation_multiplier
        self.contribution_threshold = contribution_threshold
        self.backtest = backtest
        self.backtest_n_elements = backtest_n_elements


        csv_file = f"data/{trading_pair}_OHLC_1440.csv"

        if self.backtest:
            self.data = pd.read_csv(csv_file)
            self.data = self.data.head(self.backtest_n_elements)
            self.data.set_index('timestamp', inplace=True)
            last_record = self.data.iloc[-1]
            # print(last_record,flush=True)

        else:
            self.data = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            self.data.set_index('timestamp', inplace=True)

        # Initialize exchange
        # self.exchange = ccxt.binance({
        if not backtest:
            self.exchange = ccxt.kraken({
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future'
                }
            })

    def fetch_ohlcv(self, symbol, timeframe, limit):
        ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df

    def update_data(self):
        if not self.backtest:
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
        order_submission_status
    ):
    base_message = f"{idx:04d} Timestamp: {timestamp}, Pair: {trading_pair}, Signal: {signal}, Close Price: {close_price:.2f}, Avg Position: {avg_position_price:.2f}, Total Profit: {total_profit:.2f} ({total_profit_percentage:.2f}%), Long Positions: {long_positions}, Num Positions: {num_positions}"

    if signal == "HOLD":
        pass
        # print(fg.BLUE + base_message + fg.RESET)

    elif signal == "BUY":
        base_message = f"{idx:04d} Timestamp: {timestamp}, Pair: {trading_pair}, Signal: {signal}, Close Price: {close_price:.2f}, Avg Position: {avg_position_price:.2f}, Num Positions: {num_positions}"
        if order_submission_status != "unavailable":
            print(fg.RED + base_message + fg.RESET)
        else:
            print(fg.LIGHTBLUE_EX + base_message + " unavailable" + fg.RESET)

    elif signal == "SELL":
        base_message = f"{idx:04d} Timestamp: {timestamp}, Pair: {trading_pair}, Signal: {signal}, Close Price: {close_price:.2f}, Total Profit: {fg.MAGENTA}{total_profit:.2f} ({total_profit_percentage:.2f}%){fg.GREEN}"
        print(fg.GREEN + base_message + fg.RESET)

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

    def add_trade(self, timestamp, profit, price):
        self.timestamps.append(timestamp)
        self.profits.append(profit)
        self.prices.append(price)
        if not self.cumulative_profits:
            self.cumulative_profits.append(profit)
        else:
            self.cumulative_profits.append(self.cumulative_profits[-1] + profit)

    def plot(self, initial_balance=1000):
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)
        # print(self.timestamps)
        # exit()
        dates = self.timestamps
        # Convert timestamps to datetime objects
        # dates = [datetime.strptime(ts, "%Y-%m-%d %H:%M:%S") for ts in self.timestamps]

        # Plot individual trade profits/losses
        ax1.bar(dates, self.profits, color=['g' if p > 0 else 'r' for p in self.profits])
        ax1.set_title('Individual Trade Profits/Losses')
        ax1.set_ylabel('Profit/Loss')
        ax1.axhline(y=0, color='k', linestyle='-', linewidth=0.5)

        # Plot cumulative profit and buy-and-hold value
        ax2.plot(dates, self.cumulative_profits, color='b', label='Strategy')

        # Calculate and plot buy-and-hold value
        initial_price = self.prices[0]
        buy_and_hold_values = [initial_balance * (price / initial_price) - initial_balance for price in self.prices]
        ax2.plot(dates, buy_and_hold_values, color='r', label='Buy and Hold')

        ax2.set_title('Cumulative Profit vs Buy and Hold')
        ax2.set_xlabel('Time')
        ax2.set_ylabel('Profit')
        ax2.legend()

        # Format x-axis to show dates nicely
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax2.xaxis.set_major_locator(mdates.AutoDateLocator())

        plt.gcf().autofmt_xdate()  # Rotate and align the tick labels
        plt.tight_layout()
        plt.show()

def main(trading_pair, backtest, **kwargs):

    max_positions = kwargs.get('max_positions', 3)
    negotiation_threshold = kwargs.get('negotiation_threshold', 1.0)
    limitation_multiplier = kwargs.get('limitation_multiplier', 1.5)
    contribution_threshold = kwargs.get('contribution_threshold', 1.2)
    lookback_period = kwargs.get('lookback_period', 20)
    commission_rate = kwargs.get('commission_rate', 0.001)  # Default 0.1% commission
    stop_loss_percentage = kwargs.get('stop_loss_percentage', 0.05)  # 5% stop loss
    initial_balance = kwargs.get('initial_balance', 1000)  # Initial balance for buy-and-hold calculation

    backtest_idx_iter = 0
    previous_time = ""

    # Position tracking
    current_positions = []
    total_profit = 0
    total_profit_percentage = 0
    long_positions = False
    num_positions = 0

    # Profitability tracking
    profitable_trades = 0
    non_profitable_trades = 0

    # Initialize the profit/loss plotter
    plotter = ProfitLossPlotter()

    # Buy-and-hold tracking
    initial_price = None

    while True:
        order_submission_status = ""
        try:
            strategy = TholonicStrategy(
                trading_pair=trading_pair,
                negotiation_threshold=negotiation_threshold,
                limitation_multiplier=limitation_multiplier,
                contribution_threshold=contribution_threshold,
                lookback_period=lookback_period,
                backtest=backtest,
                backtest_n_elements=backtest_idx_iter+lookback_period
            )
            latest_data = strategy.run_strategy()
            backtest_idx_iter += 1
            signal = strategy.get_signal()
            current_time = latest_data.name
            current_price = latest_data['close']

            if initial_price is None:
                initial_price = current_price

            # Break when we get to the end of the data (for backtesting)
            if current_time == previous_time:
                break
            previous_time = current_time

            # Check for stop loss
            if check_stop_loss(current_positions, current_price, stop_loss_percentage):
                signal = "SELL"
                print(fg.LIGHTYELLOW_EX + f"Stop loss ({stop_loss_percentage*100:.2f}%) triggered at {current_price:.2f}" + fg.RESET)

            # Position management
            if signal == "BUY":
                if num_positions < max_positions:
                    current_positions.append((current_price, 1))  # Buying 1 unit
                    long_positions = True
                    num_positions += 1
                    print_trading_info(
                        backtest_idx_iter,
                        current_time,
                        trading_pair,
                        signal,
                        current_price,
                        calculate_average_position_price(current_positions),
                        total_profit,
                        total_profit_percentage,
                        long_positions,
                        num_positions,
                        order_submission_status
                    )
                else:
                    order_submission_status = "unavailable"

            # Handling the SELL signal when there are open positions
            elif signal == "SELL" and current_positions:
                # Calculate the profit for closing all positions at the current price, including commission
                total_amount = sum(amount for _, amount in current_positions)
                profit, profit_percentage = calculate_profit(current_positions, current_price, total_amount, commission_rate)

                # Update profitability tracking
                if profit > 0:
                    profitable_trades += 1
                else:
                    non_profitable_trades += 1

                # Add trade to the plotter
                plotter.add_trade(current_time, profit, current_price)

                # Add the calculated profit to the total profit
                total_profit += profit
                total_profit_percentage += profit_percentage

                # Close all positions by resetting the current_positions list
                current_positions = []

                # Update flags to indicate no open positions
                long_positions = False
                num_positions = 0

                print_trading_info(
                    backtest_idx_iter,
                    current_time,
                    trading_pair,
                    signal,
                    current_price,
                    0,  # avg_position_price is 0 after selling
                    total_profit,
                    total_profit_percentage,
                    long_positions,
                    num_positions,
                    order_submission_status
                )
            else:
                # Add current price to plotter for buy-and-hold comparison
                plotter.add_trade(current_time, 0, current_price)

            time.sleep(0.0)  # Wait before next update
        except KeyboardInterrupt:
            print("Strategy stopped by user.")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            time.sleep(60)  # Wait for 1 minute before retrying

    # Calculate and print profitability ratio
    total_trades = profitable_trades + non_profitable_trades
    if total_trades > 0:
        profit_ratio = profitable_trades / total_trades
        print(fg.CYAN + f"\nProfitability Summary:" + fg.RESET)
        print(f"Total Trades: {total_trades}")
        print(f"Profitable Trades: {profitable_trades}")
        print(f"Non-Profitable Trades: {non_profitable_trades}")
        print(f"Profit Ratio: {profit_ratio:.2%}")
        print(f"Total Profit: {total_profit:.2f} ({total_profit_percentage:.2f}%)")

        # Calculate buy-and-hold return
        buy_and_hold_return = (current_price - initial_price) / initial_price * 100
        print(f"Buy-and-Hold Return: {buy_and_hold_return:.2f}%")
    else:
        print(fg.CYAN + f"\nNo trades were executed during the backtest." + fg.RESET)

    # Plot the profits and losses
    plotter.plot(initial_balance)

if __name__ == "__main__":

    backtest = True
    trading_pair = "BTCUSD"  # You can change this to any pair supported by the exchange
    max_positions = 2
    negotiation_threshold = 1.0
    limitation_multiplier = 1.5
    contribution_threshold = 1.2
    lookback_period = 20
    commission_rate = 0.001  # 0.1% commission
    stop_loss_percentage = 0.05  # 5% stop loss
    initial_balance = 1000  # Initial balance for buy-and-hold calculation

    main(
        trading_pair,
        backtest,
        max_positions=max_positions,
        negotiation_threshold=negotiation_threshold,
        limitation_multiplier=limitation_multiplier,
        contribution_threshold=contribution_threshold,
        lookback_period=lookback_period,
        commission_rate=commission_rate,
        stop_loss_percentage=stop_loss_percentage,
        initial_balance=initial_balance
    )