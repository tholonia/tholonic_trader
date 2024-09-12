#!/bin/env python
"""
This is a test version of the trading bot that uses a single thread to process a single window of data.
It is used to test the performance of the trading bot in a single thread environment.


"""

import pandas as pd
import numpy as np
import sys
import getopt
from TholonicStrategyClass import TholonicStrategy
from DataManagerClass import DataManager
from SentimentClass import OHLCSentimentAnalyzer
from ExcelReporterClass import ExcelReporter
import toml
import trade_bot_lib as t
import trade_bot_vars as v #! holds global vars
from colorama import Fore as fg
from pprint import pprint
import os
from openpyxl.utils import get_column_letter

#!┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
#!┃ main                                                                    ┃
#!┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

if __name__ == "__main__":
    argv = sys.argv[1:]

    configfile = "trading_bot_config.toml"

    try:
        opts, args = getopt.getopt(argv, "hc:", ["help","config="])
    except getopt.GetoptError:
        t.print_testvarsusage()
        sys.exit(2)

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            t.print_testvarsusage()
            sys.exit()
        if opt in ("-c", "--config"):
            configfile = arg

    # Load configuration from TOML file
    with open(configfile, 'r') as config_file: config = toml.load(config_file)

    # Load vars locally
    csv_file = config['datamanager']['csv_file']
    from_date = config['datamanager']['start_date']
    to_date = config['datamanager']['end_date']

    # Strategy parameters
    rolling_window_size = config['cfg']['lookback_period']
    reportfilename = config['cfg']['reportfilename']
    max_loops = config['cfg']['max_loops']

    # set initial values
    limitCounter = 0
    trade_counter = 0
    iterCounter = 0
    entry_price = 0
    exit_price = 0
    position = 0 # hold the number of open trades


    # create the excel file
    try: os.unlink("output.xlsx")
    except: pass
    xlsx_reporter = ExcelReporter("output.xlsx")
    xlsx_reporter.load_or_create_workbook()
    header = ['FromDate','ToDate','N','L','C','K','Total Return','NumTrades','Win Rate','%/HODL','InSent','OutSent']
    xlsx_reporter.write_header(header)

    #! work in progress
    # # Add the formula column
    # hold_column = get_column_letter(header.index('%/HODL') + 1)
    # # xlsx_reporter.add_formula_column(get_column_letter(len(header) + 1),f"{hodl_column}{{row}}*1000","Return (%)")


    # instantiate the dataloader to handl all the source data retrieval and manipulation
    loader = DataManager()
    loader.data = loader.load_full_csv()


    """
    Each market type ('mtype' as a category, 'sentiment' as a value) has different optimal values
    for the strategy that are stored in a array in the config file.
    The mtypes are:
        1 = Sideways, 2 = Strong Bull, 3 = Bear, 4 = Strong Bull, 5 = Bull
        6 = High Resistance, 7 = Strong Support, 8 = High Volatility, 9 = Neutral, 10=Mixed

    'simulation' refers to the simulation mode, where the strategy is run as closely as
    possible to a real-time live run, except that the strategy is run on a rolling window
    of data, and the results are stored in a CSV file.

    'backtest' (UNIMPLEMENTED) refers to the backtest mode, where the strategy is run on a range of data,
    and the results are stored in a CSV file.

    """
    sentiments_ary = config['simulation'] #! holds the optimal values for each mtype


    for rolling_window_position in range(loader.get_windows_count()):
        ohlc_data = loader.get_rolling_window(window_locations=[rolling_window_position,1])
        # Nested loops for parameter combinations
        # apiout = True #
        sentiment_analyzer = OHLCSentimentAnalyzer(apiout=True) # True=no console output

        # analyze the ohlc data and return a sentiment value 1-10
        sentiment = sentiment_analyzer.analyze(pd.DataFrame(ohlc_data))

        #TODO: add swith to load relative to the mode
        # get the range of values for the sentiment based on the current sentiment
        negRange = sentiments_ary[str(sentiment)]['negRange']
        limRange = sentiments_ary[str(sentiment)]['limRange']
        conRange = sentiments_ary[str(sentiment)]['conRange']
        kRange = sentiments_ary[str(sentiment)]['kRange']


        # in simulation mode each for loop occurs only once.
        # in backtest mode, each for loop occurs for each step in the range defined in the array
        for negCounter in np.arange(*negRange):
            for limCounter in np.arange(*limRange):
                for conCounter in np.arange(*conRange):
                    for lookCounter in np.arange(*kRange): # this will probably stay at 16, based on tests done
                        """
                        The CSV input data looks like:

                        timestamp,open,high,low,close,volume
                        2023-07-27 00:00:00,29298.53,29363.11,29350.88,29355.07,282.21147203
                        2023-07-27 01:00:00,29335.85,29419.74,29355.07,29400.14,172.24982198
                        2023-07-27 02:00:00,29344.42,29438.55,29400.14,29426.53,164.70539073
                        (9529 data lines)

                        """
                        if sentiment in [1,2,3,6,7,8,9,10]: # these are the mtypes to use
                            t.status_line(
                                 sentiment=sentiment,
                                 trade_counter=trade_counter,
                                 rolling_window_position=rolling_window_position,
                                 negCounter=negCounter,
                                 limCounter=limCounter,
                                 conCounter=conCounter,
                                 lookCounter=lookCounter
                            )

                            strategy = TholonicStrategy(
                                negotiation_threshold=negCounter,
                                limitation_multiplier=limCounter,
                                contribution_threshold=conCounter,
                                ohlc_data=ohlc_data,
                                sentiment=sentiment,
                            )
                            """
                            strategy.data df now looks like:
                                                    open      high       low     close      volume
                            timestamp
                            2023-07-27 00:00:00  29298.53  29363.11  29350.88  29355.07  282.211472
                            2023-07-27 01:00:00  29335.85  29419.74  29355.07  29400.14  172.249822
                            2023-07-27 02:00:00  29344.42  29438.55  29400.14  29426.53  164.705391
                            2023-07-27 03:00:00  29402.01  29450.90  29429.20  29403.57  132.702561
                            2023-07-27 04:00:00  29403.56  29491.05  29403.57  29484.50  157.321089

                            """
                            strategy.run_strategy()  # original CPU code
                            """
                            With original CPU code: 2m30s to process 1 window; 550 windows = 23 hrs
                            With torch and gpu:     1m45s to process 1 window; 550 windows = 16 hrs
                            With torch and no gpu:  1m55s to process 1 window; 550 windows = 18 hrs
                            """

                            # strategy.run_strategy_torch() #! mangles the buy_condition values

                            """
                            The df now looks like
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

                            # trades can have multiple buys and sells within the window, so it's a list of dicts
                            trades, position = strategy.backtest()

                            """
                            trades is a list of dicts:

                                {
                                    'entry_date': Timestamp('2023-07-27 10:00:00'),
                                    'entry_price': 29481.9,
                                    'entry_sentiment': 1,
                                    'exit_date': Timestamp('2023-07-27 11:00:00'),
                                    'exit_price': 29509.28,
                                    'exit_sentiment': 1
                                }
                            """

                            for trade in trades:
                                trade_counter += 1
                                trades_df =pd.DataFrame(trade,index=[0])

                                performance = strategy.calculate_performance(trades_df) # this is a dict
                                if performance is None:
                                    break

                                if performance['Return'] is not None and performance['Return'] > 0:

                                    inon = performance['inon'] # inon = buy action performed in what sentiment
                                    outon = performance['outon'] # outon = sell action performed in what sentiment
                                    row = [
                                        f"{trades_df['entry_date'].to_string()}",
                                        f"{trades_df['exit_date'].to_string()}",
                                        f"{negCounter:.2f}",
                                        f"{limCounter:.2f}",
                                        f"{conCounter:.2f}",
                                        f"{lookCounter:.0f}",
                                        f"{performance['Return']:.5f}",
                                        f"{performance['Trades']:.0f}",
                                        f"{performance['Profit']:.5f}",
                                        f"{performance['StratOverHodl']:.5f}",
                                        f"{inon}",
                                        f"{outon}",
                                        ]
                                    # save to interactive table in xslx
                                    xlsx_reporter.append_row(row)
                                    xlsx_reporter.adjust_column_width()
                                    xlsx_reporter.add_table()
                                    xlsx_reporter.save()

                                    #! add these two columns to the xslx sheet
                                    #~ =M1*(J2+1), =N1*(G2+1)

                                    iterCounter += 1
                                    if limitCounter > max_loops:
                                        exit()

    print(f"Results have been written to {reportfilename} [{iterCounter}]")