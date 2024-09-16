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
from colorama import Fore as fg
from pprint import pprint
import os
from openpyxl.utils import get_column_letter
from openpyxl.styles import numbers
# from GlobalsClass import trade_counter



#!┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
#!┃ main                                                                    ┃
#!┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

if __name__ == "__main__":
    argv = sys.argv[1:]

    configfile = "trading_bot_config.toml"
    testvars_report_filename = "testvars_fast.xlsx"

    try:
        opts, args = getopt.getopt(argv, "hc:r:", ["help","config=","report="])
    except getopt.GetoptError:
        t.print_testvarsusage()
        sys.exit(2)

    # first get any specific config file
    for opt, arg in opts:
        if opt in ("-c", "--config"):
            configfile = arg

    # Load all defaults configurations from TOML file
    with open(configfile, 'r') as config_file:
        config = toml.load(config_file)

        csv_file = config['datamanager']['csv_file']
        from_date = config['datamanager']['start_date']
        to_date = config['datamanager']['end_date']
        mtype_includes = config['datamanager']['mtype_includes']
        rolling_window_size = config['datamanager']['window_size']
        testvars_report_filename = config['logging']['testvars_report_filename']
        max_loops = config['cfg']['max_loops']

    # OVERRIDE any of the above with command line arguments
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            t.print_testvarsusage()
            sys.exit()
        if opt in ("-r", "--report"):
            testvars_report_filename = arg


    # set initial values
    csv_lines = t.count_csv_lines(csv_file)
    iterCounter = 0
    iterCounter = 0
    entry_price = 0
    exit_price = 0
    # position = 0 # hold the number of open trades
    running_profit = 0
    trxgain = 0
    oHODL_cum = 0

    last_trade_counter = 0

    tradestore = []
    # create the excel file
    try: os.unlink(testvars_report_filename)
    except: pass
    xlsx_reporter = ExcelReporter(testvars_report_filename)
    xlsx_reporter.load_or_create_workbook()
    header = [
        'idx',
        'FromDate',
        'ToDate',
        'EntryPrice',
        'ExitPrice',
        'N',
        'L',
        'C',
        'K',
        'trx_return',
        'cum_return',
        'trx_overhodl',
        'cum_overhodl',
        'entry_sentiment',
        'exit_sentiment',
        'price_change',
        'trend',
        '% avg_body_size',
        '% avg_upper_wick',
        '% avg__lower_wick',
        '% volatility',
    ]
    xlsx_reporter.write_header(header)


    # instantiate the dataloader to handle all the source data retrieval and manipulation
    loader = DataManager()
    loader.data = loader.load_full_csv()

    all_rows = []
    all_trades = []
    batch_size = 1000
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
    sentiments_ary = config['simulation'] #! holds the optimal AVERAGE values for each mtype
    # sentiments_ary = config['best'] #! holds the BEST values for each mtype

    line_counter = 0
    # for rolling_window_position in range(loader.get_windows_count()):
    for rolling_window_position in range(len(loader.data)-rolling_window_size):
        print(f"{line_counter}/{csv_lines}", end="\r")
        line_counter += 1

        ohlc_data = loader.get_rolling_window(window_locations=[rolling_window_position,1])

        # t.xprint(ohlc_data,pp=True,co=fg.MAGENTA,ex=False)
        # Nested loops for parameter combinations
        # apiout = True #
        sentiment_analyzer = OHLCSentimentAnalyzer(apiout=True) # True=no console output

        # analyze the ohlc data and return a sentiment value 1-10
        try:
            sentiment, sentiment_metadata_ary = sentiment_analyzer.analyze(pd.DataFrame(ohlc_data))
            # print(">>>",sentiment)
            # exit()
        except Exception as e:
            print(f"Error analyzing sentiment: {e}")
            break

        # get the range of values for the sentiment based on the current sentiment
        negRange = sentiments_ary[str(sentiment)]['negRange']
        limRange = sentiments_ary[str(sentiment)]['limRange']
        conRange = sentiments_ary[str(sentiment)]['conRange']
        kRange   = sentiments_ary[str(sentiment)]['kRange']


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
                        if sentiment in mtype_includes: # these are the mtypes to use

                            strategy = TholonicStrategy(
                                negotiation_threshold=negCounter,
                                limitation_multiplier=limCounter,
                                contribution_threshold=conCounter,
                                ohlc_data=ohlc_data,
                                sentiment=sentiment,
                                configfile=configfile,
                            )
                            strategy.data['timestamp'] = strategy.data.index
                            tsd = strategy.data['timestamp'].iloc[-1]

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
                            strategy =strategy.run_strategy()  # original CPU code
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
                            strategy, trade_counter = strategy.backtest()  # updates strategy.trades[] with appended trades
                            #! check here for an existing exit_date, and break if it doesn;t exist
                            if 'exit_date' in strategy.trades.columns and not strategy.trades.empty:
                                # Get the last 'exit_date' value
                                last_exit_date = strategy.trades['exit_date'].iloc[-1]
                                # Check if 'exit_date' is NaT (i.e., trade is still open)
                                if pd.isna(last_exit_date):
                                    # The last trade has not been closed; decide to break or handle accordingly
                                    break
                                else:
                                    # The last trade has been closed; continue processing or handle as needed
                                    pass
                            else:
                                # Either 'exit_date' does not exist or there are no trades
                                # Handle accordingly, e.g., continue or break
                                break

                            """
                            strategy.trades is a list of dicts:

                                [{
                                    'entry_date': Timestamp('2023-07-27 10:00:00'),
                                    'entry_price': 29481.9,
                                    'entry_sentiment': 1,
                                    'exit_date': Timestamp('2023-07-27 11:00:00'),
                                    'exit_price': 29509.28,
                                    'exit_sentiment': 1
                                },
                                ...
                                ]
                            """

                            if last_trade_counter != trade_counter: # this avoids registering buys that exceed position limit of 1
                                try:
                                    t.status_line(
                                        sentiment=sentiment,
                                        trade_counter=trade_counter,
                                        rolling_window_position=rolling_window_position,
                                        negCounter=negCounter,
                                        limCounter=limCounter,
                                        conCounter=conCounter,
                                        lookCounter=lookCounter,
                                        limitCounter=iterCounter,
                                        enter_date=str(strategy.trades['entry_date'].iloc[-1]),
                                    )
                                    last_trade_counter = trade_counter
                                    row = [
                                        iterCounter,
                                        f"{strategy.trades['entry_date'].iloc[-1]}",
                                        f"{strategy.trades['exit_date'].iloc[-1]}",
                                        strategy.trades['entry_price'].iloc[-1],
                                        strategy.trades['exit_price'].iloc[-1],
                                        negCounter,
                                        limCounter,
                                        conCounter,
                                        lookCounter,
                                        strategy.trades['trx_return'].iloc[-1],
                                        strategy.trades['cum_return'].iloc[-1],
                                        strategy.trades['trx_overhodl'].iloc[-1],
                                        strategy.trades['cum_overhodl'].iloc[-1],
                                        strategy.trades['entry_sentiment'].iloc[-1],
                                        strategy.trades['exit_sentiment'].iloc[-1],
                                        sentiment_metadata_ary['price_change'],
                                        sentiment_metadata_ary['trend'],
                                        sentiment_metadata_ary['average_body_size'],
                                        sentiment_metadata_ary['average_upper_wick'],
                                        sentiment_metadata_ary['average_lower_wick'],
                                        sentiment_metadata_ary['volatility'],
                                    ]

                                    all_rows.append(row)
                                    batch_size = 100  # Adjust based on your needs
                                    if iterCounter % batch_size == 0:
                                        # Write the current batch to Excel
                                        batch_df = pd.DataFrame(all_rows, columns=header)
                                        if os.path.exists(testvars_report_filename):
                                            # Append to existing file
                                            with pd.ExcelWriter(testvars_report_filename, mode='a', engine='openpyxl', if_sheet_exists='overlay') as writer:
                                                # Get the last row in the existing Excel sheet
                                                startrow = writer.sheets['Sheet1'].max_row
                                                batch_df.to_excel(writer, index=False, header=False, startrow=startrow)
                                        else:
                                            # File does not exist, create it and write the header
                                            with pd.ExcelWriter(testvars_report_filename, mode='w', engine='openpyxl') as writer:
                                                batch_df.to_excel(writer, index=False, header=True)
                                        # Clear the batch
                                        all_rows = []


                                    #! add these two columns to the xslx sheet
                                    #~ =M1*(J2+1), =N1*(G2+1)
                                except Exception as e:
                                    # pass
                                    print(f"Error in status_line: {e}")


                        if iterCounter > max_loops or iterCounter >= csv_lines-rolling_window_position:
                            xlsx_reporter = ExcelReporter(testvars_report_filename)
                            xlsx_reporter.load_or_create_workbook()
                            xlsx_reporter.adjust_column_width()
                            xlsx_reporter.set_column_format("J","0.00%")
                            xlsx_reporter.set_column_format("K","0.00%")
                            xlsx_reporter.set_column_format("L","0.00%")
                            xlsx_reporter.set_column_format("M","0.00%")
                            xlsx_reporter.set_column_format("D","$0")
                            xlsx_reporter.set_column_format("E","$0")
                            xlsx_reporter.add_table()
                            xlsx_reporter.save()
                            exit()
                        iterCounter += 1



    print(f"Results have been written to {testvars_report_filename} [{iterCounter}]")