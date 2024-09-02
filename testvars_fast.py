#!/bin/env python

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import csv
import sys
import getopt
import os, sys, time
from decimal import Decimal, ROUND_HALF_UP

def print_usage():
    str = f"""
    Usage: python testvars_fast.py -t <time_test_option>

    Time Test Options:
      Coinbase-BTC-13mo-60
      Kraken-BTC-1mo-60
      LongBull
      MedBull
      ShortBull
      LongBear
      MedBear
      ShortBear
      ShortFlat
      MedFlat
"""



class TholonicStrategy:
    def __init__(self, csv_file, negotiation_threshold, limitation_multiplier, contribution_threshold, lookback_period):
        # Read CSV file
        self.data = pd.read_csv(csv_file, parse_dates=['timestamp'])
        self.data.set_index('timestamp', inplace=True)
        self.data.sort_index(inplace=True)

        # Strategy parameters
        self.lookback = lookback_period
        self.negotiation_threshold = negotiation_threshold
        self.limitation_multiplier = limitation_multiplier
        self.contribution_threshold = contribution_threshold

    def set_date_range(self, time_test_option):
        if time_test_option == "Coinbase-BTC-13mo-60":
            self.start_date = datetime(2023, 7, 27)
            self.end_date = datetime(2024, 8, 27)
        if time_test_option == "Kraken-BTC-1mo-60":
            self.start_date = datetime(2022, 9, 6)
            self.end_date = datetime(2024, 8, 25)

        elif time_test_option == "LongBull":
            self.start_date = datetime(2023, 10, 5)
            self.end_date = datetime(2023, 12, 20)
        elif time_test_option == "MedBull":
            self.start_date = datetime(2024, 1, 17)
            self.end_date = datetime(2024, 3, 13)
        elif time_test_option == "ShortBull":
            self.start_date = datetime(2024, 5, 2)
            self.end_date = datetime(2024, 6,6)

        elif time_test_option == "LongBear":
            self.start_date = datetime(2024, 3,13)
            self.end_date = datetime(2024, 5,2)
        elif time_test_option == "MedBear":
            self.start_date = datetime(2024, 6,6)
            self.end_date = datetime(2024, 7,5)
        elif time_test_option == "ShortBear":
            self.start_date = datetime(2024,7,27)
            self.end_date = datetime(2024, 8,6)


        elif time_test_option == "SHortFlat":
            self.start_date = datetime(2024, 2,13)
            self.end_date = datetime(2024, 2, 27)
        elif time_test_option == "MedFlat":
            self.start_date = datetime(2024, 12, 6)
            self.end_date = datetime(2024, 1, 8)


        else:  # Default
            self.start_date = self.data.index[0]
            self.end_date = self.data.index[-1]

        self.data = self.data[(self.data.index >= self.start_date) & (self.data.index <= self.end_date)]

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

    def backtest(self):
        position = 0
        entry_price = 0
        trades = []

        for i, row in self.data.iterrows():
            if position == 0 and row['buy_condition']:
                position = 1
                entry_price = row['close']
                trades.append({'entry_date': i, 'entry_price': entry_price})
            elif position == 1 and row['sell_condition']:
                position = 0
                exit_price = row['close']
                trades[-1].update({'exit_date': i, 'exit_price': exit_price})

        return pd.DataFrame(trades)

    def run_strategy(self, time_test_option):
        self.set_date_range(time_test_option)
        self.calculate_indicators()
        self.generate_signals()
        return self.backtest()

    def calculate_performance(self, trades):
        if not trades.empty:
            trades['return'] = (trades['exit_price'] - trades['entry_price']) / trades['entry_price']
            total_return = (trades['return'] + 1).prod() - 1
            num_trades = len(trades)
            win_rate = (trades['return'] > 0).mean()

            buy_and_hold_return = (self.data['close'].iloc[-1] - self.data['close'].iloc[0]) / self.data['close'].iloc[0]
            strat_over_hodl = total_return - buy_and_hold_return
            return {
                'Return': total_return,
                'Trades': num_trades,
                'Profit': win_rate,
                'StratOverHodl': strat_over_hodl,
                # 'Buy and Hold Return': f"{win_rate-buy_and_hold_return:.2f}"
            }
        # else:
            # return "No trades were executed."

def limit_decimals(number, decimals=2):
    return float(Decimal(str(number)).quantize(Decimal(f"0.{'0'*decimals}"), rounding=ROUND_HALF_UP))
def count_csv_lines(file_path):
    with open(file_path, 'r') as file:
        return sum(1 for row in csv.reader(file))

if __name__ == "__main__":
    argv = sys.argv[1:]
    time_test_option = False

    try:
        opts, args = getopt.getopt(argv, "ht:",["help", "time="])
    except getopt.GetoptError:
            print_usage()
            sys.exit(2)


    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print_usage()
            sys.exit()
        elif opt in ("-t", "--time"):
            time_test_option = arg

    csv_file = '/home/jw/src/cbot/data/BTC_USD_OHLC_60_20230727_20240827.csv'  # Replace with your CSV file path
    # entries = count_csv_lines(csv_file)
    # print(f"Entries: {entries}")

    # negotiation_threshold = 3.0
    # limitation_multiplier = 2.0
    # contribution_threshold = 3
    # lookback_period    = 14


    iterCounter = 0
    reportfilename = f'strategy_results_60_{time_test_option}.csv'

    with open(reportfilename, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)

        # Write the header row
        header = ['Time Test Option', 'Negotiation Threshold', 'Limitation Multiplier',
                'Contribution Threshold', 'Lookback Period', 'Total Return',
                'Number of Trades', 'Win Rate', 'StarOverHodl']
        csvwriter.writerow(header)

    # Nested loops for parameter combinations
        for negCounter in np.arange(0, 4, 0.1):
            for limCounter in np.arange(0, 2, 0.1):
                for conCounter in np.arange(1, 5, 0.2):
                    for lookCounter in [16]: #np.arange(14, 28, 1):
                        print(f"n: {negCounter:01.1f}\tl:{limCounter:01.1f}\tc:{conCounter:01.1f}\tL:{lookCounter:02d}                ", file=sys.stderr, end="\r")
                        # print(f"Time Test Option: {time_test_option}, Total Return: {performance['Return']}, Number of Trades: {performance['Trades']}, Win Rate: {performance['Profit']}")
                        strategy = TholonicStrategy(csv_file, negCounter, limCounter, conCounter, lookCounter)
                        trades = strategy.run_strategy(time_test_option)
                        performance = strategy.calculate_performance(trades)

                        try:
                            # print(len(trades) * 0.0005)
                            # print(performance['Return'])
                            min_return = (len(trades) * 0.006)

                            # if performance['Return'] > min_return: #0.2: # 2.5:
                            if performance['Return'] > 0:


                                try:
                                    # Prepare the row data
                                    row = [
                                        time_test_option,
                                        f"{negCounter:.1f}",
                                        f"{limCounter:.1f}",
                                        f"{conCounter:.1f}",
                                        f"{lookCounter:02d}",
                                        f"{performance['Return']:.5f}",
                                        f"{performance['Trades']:.0f}",
                                        f"{performance['Profit']:.5f}",
                                        f"{performance['StratOverHodl']:.5f}"
                                        ]
                                    # row.extend(performance.values())
                                    # print(performance.values())

                                    # Write the row to the CSV file
                                    csvwriter.writerow(row)

                                    # Optional: Print the row to console
                                    # print(f"{time_test_option}, {negCounter:.1f}", {limCounter:.1f},  {conCounter:.1f} {lookCounter:02d}"]

                                    print(f"[{min_return:.5f}]",', '.join(map(str, row)))
                                except Exception as e:
                                    print(f"Error occurred: {e}")
                                    continue
                                iterCounter += 1
                                # if limitCounter > 100: exit()
                        except Exception as e:
                            pass
    print(f"Results have been written to {reportfilename} [{iterCounter}]")