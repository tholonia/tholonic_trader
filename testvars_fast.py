#!/bin/env python
"""
testvars_fast.py: Fast Testing Script for Trading Strategy

This script is designed to quickly test various configurations of the trading strategy
using predefined time periods and market conditions. It allows for rapid evaluation
of the TholonicStrategy across different scenarios.

Key Features:
1. Command-line interface for selecting test scenarios
2. Integration with TholonicStrategy and DataLoader classes
3. Support for multiple predefined test cases (e.g., bull, bear, flat markets)
4. Efficient data processing and strategy evaluation
5. Customizable test parameters through command-line options

Usage:
Run this script from the command line with the -t or --time option to specify
the test scenario. Use -h or --help to display usage information.

Example:
    python testvars_fast.py -t LongBull

Dependencies:
- pandas: For data manipulation
- numpy: For numerical operations
- TholonicStrategyClass: For implementing the trading strategy
- DataLoaderClass: For loading and preprocessing market data
- trade_bot_vars: For accessing shared variables and configurations
- colorama: For colored console output

Note: Ensure all dependencies are installed and properly configured before
running this script. Refer to the project documentation for setup instructions.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import csv
import sys
import getopt
import os, sys, time
from decimal import Decimal, ROUND_HALF_UP
import traceback
from TholonicStrategyClass import TholonicStrategy
from DataLoaderClass import DataLoader

import trade_bot_vars as v
from colorama import Fore as fg
def print_colored(text, color):
    """
    Print text in the specified color.

    Args:
    text (str): The text to be printed.
    color (colorama.Fore): The color to use for printing.

    Returns:
    None
    """
    print(color + text + fg.RESET)

def format_number(number, decimals=2):
    """
    Format a number to a specified number of decimal places.

    Args:
    number (float): The number to be formatted.
    decimals (int): The number of decimal places to round to. Default is 2.

    Returns:
    str: The formatted number as a string.
    """
    return f"{number:.{decimals}f}"

def calculate_percentage(part, whole):
    """
    Calculate the percentage of a part relative to a whole.

    Args:
    part (float): The part value.
    whole (float): The whole value.

    Returns:
    float: The calculated percentage.
    """
    return (part / whole) * 100 if whole != 0 else 0

def parse_date(date_string):
    """
    Parse a date string into a datetime object.

    Args:
    date_string (str): The date string to parse.

    Returns:
    datetime: The parsed datetime object.
    """
    return datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")

def calculate_time_difference(start_date, end_date):
    """
    Calculate the time difference between two dates.

    Args:
    start_date (datetime): The start date.
    end_date (datetime): The end date.

    Returns:
    timedelta: The time difference.
    """
    return end_date - start_date

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

    trade_counter = 0
    iterCounter = 0
    reportfilename = f'strategy_results_60_{time_test_option}.csv'

    entry_price = 0
    exit_price = 0
    v.position = 0 # set initial buy tracking value to buy (0)

    with open(reportfilename, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)

        # Write the header row
        header = ['Time Test Option', 'Negotiation Threshold', 'Limitation Multiplier',
                'Contribution Threshold', 'Lookback Period', 'Total Return',
                'Number of Trades', 'Win Rate', 'StarOverHodl','Entry Sentiment','Exit Sentiment']
        csvwriter.writerow(header)


        # ohlcfile=csv_file,
        from_date="2023-07-27 00:00:00"
        to_date="2024-08-27 00:00:00"


        for rolling_window_position in range(595): # int 9529/16
            loader = DataLoader(csv_file, from_date, to_date, 16)
            loader.shift_window(rolling_window_position)
            ohlc_data = loader.get_data()
            # print(ohlc_data.head())
            # Nested loops for parameter combinations
            for negCounter in np.arange(0.1, 4.0, 0.1):
                for limCounter in np.arange(0.0, 2.0, 0.1):
                    for conCounter in np.arange(1.0, 5.0, 0.1):
                        for lookCounter in [16]: #np.arange(14, 28, 1):
                            spacer = "          " # spacer to make room for "No Trades" in the output
                            print( f"  {trade_counter:6d}:{rolling_window_position:4d}  \tn:{fg.LIGHTCYAN_EX}{negCounter:01.1f}{fg.RESET}\tl:{fg.LIGHTMAGENTA_EX}{limCounter:01.1f}{fg.RESET}\tc:{fg.LIGHTGREEN_EX}{conCounter:01.1f}{fg.RESET}\tk:{fg.LIGHTRED_EX}{lookCounter:02d}{fg.RESET}                ", file=sys.stderr, end="\r",flush=True)
                            """
                            The CSV input data looks like:

                            timestamp,open,high,low,close,volume
                            2023-07-27 00:00:00,29298.53,29363.11,29350.88,29355.07,282.21147203
                            2023-07-27 01:00:00,29335.85,29419.74,29355.07,29400.14,172.24982198
                            2023-07-27 02:00:00,29344.42,29438.55,29400.14,29426.53,164.70539073
                            (9529 data lines)

                            """

                            strategy = TholonicStrategy(
                                trading_pair="BTCUSD",
                                negotiation_threshold=negCounter,
                                limitation_multiplier=limCounter,
                                contribution_threshold=conCounter,
                                lookback_period=lookCounter,
                                livemode=False,
                                livemode_n_elements=lookCounter,
                                ohlc_data=ohlc_data,
                                # ohlcfile=csv_file,
                                # from_date="2023-07-27",
                                # to_date="2024-08-27",
                            )
                            # the df now looks like:
                            """
                            open      high       low     close      volume
    timestamp
    2023-07-27 00:00:00  29298.53  29363.11  29350.88  29355.07  282.211472
    2023-07-27 01:00:00  29335.85  29419.74  29355.07  29400.14  172.249822
    2023-07-27 02:00:00  29344.42  29438.55  29400.14  29426.53  164.705391
    2023-07-27 03:00:00  29402.01  29450.90  29429.20  29403.57  132.702561
    2023-07-27 04:00:00  29403.56  29491.05  29403.57  29484.50  157.321089

                            """
                            strategy.run_strategy()
                            #the df now looks like
                            """
                            open      high       low     close      volume  price_change  average_volume  volatility  average_volatility  negotiation_condition  limitation_condition  contribution_condition  buy_condition  sell_condition  sentiment
    timestamp
    2023-07-27 00:00:00  29298.53  29363.11  29350.88  29355.07  282.211472      0.192979             NaN         NaN                 NaN                   True                 False                   False          False           False          1
    2023-07-27 01:00:00  29335.85  29419.74  29355.07  29400.14  172.249822      0.219152             NaN         NaN                 NaN                   True                 False                   False          False           False          1
    2023-07-27 02:00:00  29344.42  29438.55  29400.14  29426.53  164.705391      0.279815             NaN         NaN                 NaN                   True                 False                   False          False           False          1
    2023-07-27 03:00:00  29402.01  29450.90  29429.20  29403.57  132.702561      0.005306             NaN         NaN                 NaN                   True                 False                   False          False           False          1
    2023-07-27 04:00:00  29403.56  29491.05  29403.57  29484.50  157.321089      0.275273             NaN         NaN                 NaN                   True                 False                   False          False           False          1


                            Varios fields are added:
                                strategy.show_data(strategy.data)
                                    strategy.run_strategy()
                                    open                      float64
                                    high                      float64
                                    low                       float64
                                    close                     float64
                                    volume                    float64
                                    price_change              float64
                                    average_volume            float64
                                    volatility                float64
                                    average_volatility        float64
                                    negotiation_condition        bool
                                    limitation_condition         bool
                                    contribution_condition       bool
                                    buy_condition                bool
                                    sell_condition               bool
                                    sentiment                   int64
                                    dtype: object

                            """

                            trades = strategy.backtest()


                            # print(f"len(trades): |{len(trades)}|")
                            # print(type(trades))

                            """
                            trades_df, when not False, is a dataframe of the dict:

                                {
                                    'entry_date': Timestamp('2023-07-27 10:00:00'),
                                    'entry_price': 29481.9,
                                    'entry_sentiment': 1,
                                    'exit_date': Timestamp('2023-07-27 11:00:00'),
                                    'exit_price': 29509.28,
                                    'exit_sentiment': 1
                                }
                            """

                            if len(trades) <4== 0:
                                break
                            else:
                                trade_counter += 1
                                trades_df =pd.DataFrame(trades)

                            # strategy.show_data(trades_df)
                            # exit()
                            try:
                                performance = strategy.calculate_performance(trades_df)
                            except Exception as e:
                                break
                            # print(performance)
                            # exit()


                            try:
                                # min_return = (len(trades) * 0.006)

                                # if performance['Return'] > min_return: #0.2: # 2.5:
                                if performance['Return'] is not None and performance['Return'] > 0:
                                    try:
                                        # Prepare the row data

                                        inon = performance['inon']
                                        outon = performance['outon']
                                        row = [
                                            "time_test_option",
                                            f"{negCounter:.1f}",
                                            f"{limCounter:.1f}",
                                            f"{conCounter:.1f}",
                                            f"{lookCounter:02d}",
                                            f"{performance['Return']:.5f}",
                                            f"{performance['Trades']:.0f}",
                                            f"{performance['Profit']:.5f}",
                                            f"{performance['StratOverHodl']:.5f}",
                                            f"{inon}",
                                            f"{outon}",
                                            ]
                                        # row.extend(performance.values())
                                        # print(performance.values())

                                        # Write the row to the CSV file
                                        csvwriter.writerow(row)


                                        # Optional: Print the row to console
                                        # print(f"{time_test_option}, {negCouimport tracebacknter:.1f}", {limCounter:.1f},  {conCounter:.1f} {lookCounter:02d}"]

                                        # print(', '.join(map(str, row)))
                                        # try:
                                        #     print(f"        n: {negCounter:01.1f}\tl:{limCounter:01.1f}\tc:{conCounter:01.1f}\tL:{lookCounter:02d} {v.snt[int(inon)]} {v.snt[outon]}                 ", file=sys.stderr, end="\r")
                                        # except:
                                        #     pass

                                    except Exception as e:
                                        pass
                                        # print(f"An error occurred: {e}")
                                        # traceback.print_exc()
                                        # exit()
                                    iterCounter += 1
                                    # if limitCounter > 100: exit()
                            except TypeError as e:
                                pass
                                # print(f"[{iterCounter}] Variable out of Scope: {e}",end="\r")
                                # traceback.print_exc()
                                # exit()
                                # print(fg.RED+f"\n [OOS]  n: {negCounter:01.1f}\tl:{limCounter:01.1f}\tc:{conCounter:01.1f}\tL:{lookCounter:02d}\n"+fg.GREEN, file=sys.stderr, end="\r")



                            except Exception as e:
                                print(f"An error occurred: {e}")
                                traceback.print_exc()
                                exit()
                                pass
    print(f"Results have been written to {reportfilename} [{iterCounter}]")