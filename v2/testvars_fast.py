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
Run this script from the command line. Use -h or --help to display usage information.

Example:
    python testvars_fast.py

Dependencies:
- pandas: For data manipulation
- numpy: For numerical operations
- TholonicStrategyClass: For implementing the trading strategy
- DataLoaderClass: For loading and preprocessing market data
- trade_bot_vars: For accessing shared variables and configurations
- colorama: For colored console output
- toml: For loading TOML configuration files

Note: Ensure all dependencies are installed and properly configured before
running this script. Refer to the project documentation for setup instructions.
"""

import pandas as pd
import numpy as np
import csv
import sys
import getopt
import traceback
from TholonicStrategyClass import TholonicStrategy
from DataManagerClass import DataManager
from SentimentClass import OHLCSentimentAnalyzer
import toml
import trade_bot_lib as t
import trade_bot_vars as v #! holds global vars
from colorama import Fore as fg
from pprint import pprint

#!┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
#!┃ main                                                                    ┃
#!┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

if __name__ == "__main__":
    argv = sys.argv[1:]

    try:
        opts, args = getopt.getopt(argv, "h", ["help"])
    except getopt.GetoptError:
        t.print_testvars_usage()
        sys.exit(2)

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            t.print_testvars_usage()
            sys.exit()

    # Load configuration from TOML file
    with open('trading_bot_config.toml', 'r') as config_file:
        config = toml.load(config_file)

    # Extract variables from the config
    csv_file = config['datamanager']['csv_file']
    from_date = config['datamanager']['start_date']
    to_date = config['datamanager']['end_date']

    # Strategy parameters
    rolling_window_size = config['cfg']['lookback_period']

    # # If testvars_fast section doesn't exist, we'll use default values or add them to the TOML file
    # if 'testvars_fast' not in config:
    #     config['testvars_fast'] = {
    #         'reportfilename': 'testvars_fast_report.csv',
    #         'max_loops': 1000,
    #         'negRange': [0.1, 0.5, 1.0],
    #         'limRange': [1.0, 1.5, 2.0],
    #         'conRange': [1.0, 1.2, 1.4],
    #         'kRange': [2, 3, 4]
    #     }
    #     # Optionally, you can save the updated config back to the file
    #     # with open('trading_bot_config.toml', 'w') as config_file:
    #     #     toml.dump(config, config_file)



    reportfilename = config['cfg']['reportfilename']
    max_loops = config['cfg']['max_loops']
    negRange = config['cfg']['negRange']
    limRange = config['cfg']['limRange']
    conRange = config['cfg']['conRange']
    kRange = config['cfg']['kRange']

    # print configuration for verification
    print(fg.CYAN + "Configuration:" + fg.RESET)
    print(f"CSV File: {csv_file}")
    print(f"Date Range: {from_date} to {to_date}")
    print(f"Rolling Window Size: {rolling_window_size}")
    print(f"Report Filename: {reportfilename}")
    print(f"Max Loops: {max_loops}")
    print(f"Negotiation Range: {negRange}")
    print(f"Limitation Range: {limRange}")
    print(f"Contribution Range: {conRange}")
    print(f"K Range: {kRange}")

    # print(negRange)
    # exit()



    limitCounter = 0
    trade_counter = 0
    iterCounter = 0
    entry_price = 0
    exit_price = 0
    position = 0 # set initial buy tracking value to buy (0)

    with open(reportfilename, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)

        # Write the header row
        header = [
            'FromDate',
            'ToDate',
            'N',
            'L',
            'C',
            'K',
            'Total Return',
            'NumTrades',
            'Win Rate',
            '%/HODL',
            'InSent',
            'OutSent'
        ]
        csvwriter.writerow(header)


        # loopRange = int((t.count_csv_lines(csv_file)-1)/ rolling_window_size)


        # window_count = 46

        # loader = DataLoader(csv_file, from_date, to_date, rolling_window_size)

        print("!!!!!!")
        loader = DataManager()
        print(">>>>>>>")

        loader.data = loader.load_full_csv()
        # loader.data = loader.load_data() #source='csv', trading_pair='BTCUSD', window_size=rolling_window_size, start_date=from_date, end_date=to_date)
        # for window in enumerate(loader.create_rolling_window()):
        print(loader.data)

        # exit()
        loopRange = loader.get_windows_count()
        # t.xprint(loopRange)

        for rolling_window_position in range(loopRange):
            # loader = DataLoader(csv_file, from_date, to_date, rolling_window_size)
            # loader.shift_window(rolling_window_position)
            ohlc_data = loader.get_rolling_window(window_locations=[rolling_window_position,1])
            # Nested loops for parameter combinations
            # apiout = True
            sentiment_analyzer = OHLCSentimentAnalyzer(apiout=True)
            sentiment = sentiment_analyzer.analyze(pd.DataFrame(ohlc_data))
            # liveDebug = False
            # t.xprint(sentiment)
            print(111)
            for negCounter in np.arange(*negRange):
                for limCounter in np.arange(*limRange):
                    for conCounter in np.arange(*conRange):
                        for lookCounter in np.arange(*kRange): #! this will probably stay at 16, based on tests done
                            # print(negCounter,limCounter,conCounter,lookCounter)

                            # with open('dev.yaml', 'r') as dconfig_file:
                            #      dconfig = yaml.safe_load(dconfig_file)
                            # D = dconfig['dev']
                            # liveDebug = D['debug']


                            print( f"  T:{trade_counter:6d}: W:{rolling_window_position:.0f}  \tn:{fg.LIGHTCYAN_EX}{negCounter:.2f}{fg.RESET}\tl:{fg.LIGHTMAGENTA_EX}{limCounter:.2f}{fg.RESET}\tc:{fg.LIGHTGREEN_EX}{conCounter:.2f}{fg.RESET}\tk:{fg.LIGHTRED_EX}{lookCounter:.0f}{fg.RESET}                ", file=sys.stderr, end="\r",flush=True)
                            # print(f"  T:{trade_counter:6d}")
                            # print(f"  W:{rolling_window_position:.0f}")
                            # print(f"  n:{fg.LIGHTCYAN_EX}{negCounter:.2f}{fg.RESET}")
                            # print(f"  l:{fg.LIGHTMAGENTA_EX}{limCounter:.2f}{fg.RESET}")
                            # print(f"  c:{fg.LIGHTGREEN_EX}{conCounter:.2f}{fg.RESET}")
                            # print(f"  k:{fg.LIGHTRED_EX}{lookCounter:.0f}{fg.RESET}")

                            """
                            The CSV input data looks like:

                            timestamp,open,high,low,close,volume
                            2023-07-27 00:00:00,29298.53,29363.11,29350.88,29355.07,282.21147203
                            2023-07-27 01:00:00,29335.85,29419.74,29355.07,29400.14,172.24982198
                            2023-07-27 02:00:00,29344.42,29438.55,29400.14,29426.53,164.70539073
                            (9529 data lines)

                            """

                            strategy = TholonicStrategy(
                                # trading_pair="BTCUSD",
                                # negotiation_threshold=negCounter,
                                # limitation_multiplier=limCounter,
                                # contribution_threshold=conCounter,
                                # lookback_period=lookCounter,
                                # livemode=False,
                                # livemode_n_elements=lookCounter,
                                ohlc_data=ohlc_data,
                                sentiment=sentiment,
                            )
                            # strategy.data df now looks like:
                            """
                                                    open      high       low     close      volume
                            timestamp
                            2023-07-27 00:00:00  29298.53  29363.11  29350.88  29355.07  282.211472
                            2023-07-27 01:00:00  29335.85  29419.74  29355.07  29400.14  172.249822
                            2023-07-27 02:00:00  29344.42  29438.55  29400.14  29426.53  164.705391
                            2023-07-27 03:00:00  29402.01  29450.90  29429.20  29403.57  132.702561
                            2023-07-27 04:00:00  29403.56  29491.05  29403.57  29484.50  157.321089

                            """
                            strategy.run_strategy()  # original CPU code

                            # with original CPU code: 2m30s to process 1 window; 550 windows = 23 hrs
                            # with torch and gpu:     1m45s to process 1 window; 550 windows = 16 hrs
                            # with torch and no gpu:  1m55s to process 1 window; 550 windows = 18 hrs

                            # strategy.run_strategy_torch() #! mangles the buy_condition values

                            # print(strategy.data)
                            # print(strategy.data['sentiment'])

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

                            # tradeds can have multiple buys and sells within the window, so it's a list of dicts
                            trades, position = strategy.backtest()

                            # pprint(trades)
                            # print(trades)
                            # input("Press Enter to continue...")
                            # print(len(trades))
                            # print("==========================================================================================")

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
                            # print("----------------------------------------------------------------------",    len(trades))




                            # if len(trades) > 0:
                            #     break
                            # else:
                            # print(trades, len(trades))

                            for trade in trades:
                                # print(trade)
                                trade_counter += 1
                                trades_df =pd.DataFrame(trade,index=[0])

                                try:
                                    # n,l,c numbers too small or big will cause errors
                                    performance = strategy.calculate_performance(trades_df) # this is a dict
                                    # print(performance)
                                except Exception as e:
                                    break

                                # print(liveDebug)
                                # if liveDebug:
                                #     print(123)
                                #     print(performance)
                                try:
                                    #! limit the transactions to meet a minimum return
                                    # min_return = (len(trades) * 0.006)
                                    # if performance['Return'] > min_return: #0.2: # 2.5:

                                    if performance['Return'] is not None and performance['Return'] > 0:
                                        try:
                                            # Prepare the row data

                                            inon = performance['inon']
                                            outon = performance['outon']
                                            row = [
                                                f"{from_date}",
                                                f"{to_date}",
                                                f"{negCounter:.2f}",
                                                f"{limCounter:.2f}",
                                                f"{conCounter:.2f}",
                                                f"{lookCounter:02d}",
                                                f"{performance['Return']:.5f}",
                                                f"{performance['Trades']:.0f}",
                                                f"{performance['Profit']:.5f}",
                                                f"{performance['StratOverHodl']:.5f}",
                                                f"{inon}",
                                                f"{outon}",
                                                ]

                                            # Write the row to the CSV file
                                            # print(row)
                                            csvwriter.writerow(row)


                                            # Optional: Print the row to console
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
                                        #! use this for short testing
                                        if limitCounter > max_loops:
                                            exit()
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