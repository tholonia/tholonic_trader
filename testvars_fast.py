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
import traceback

import toml
import trade_bot_lib as t
from colorama import Fore as fg
from pprint import pprint
import os
import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.styles import numbers
from openpyxl import load_workbook
# from GlobalsClass import trade_counter
import traceback

def append_dict_to_df(df, data_dict):
    return pd.concat([df, pd.DataFrame([data_dict])], ignore_index=True)

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
    entry_price = 0
    exit_price = 0
    running_profit = 0
    trxgain = 0
    oHODL_cum = 0

    last_trade_counter = 0

    tradestore = []
    # delete existing excel file if it exists
    try: os.unlink(testvars_report_filename)
    except: pass

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

    line_counter = 0
    rdf = pd.DataFrame()



    for rolling_window_position in range(len(loader.data)-rolling_window_size):
        print(f"{line_counter}/{csv_lines}", end="\r")

        line_counter += 1

        ohlc_data = loader.get_rolling_window(window_locations=[rolling_window_position,1])

        sentiment_analyzer = OHLCSentimentAnalyzer(apiout=True) # True=no console output

        # analyze the ohlc data and return a sentiment value 1-10
        try:
            sentiment, sentiment_metadata_ary = sentiment_analyzer.analyze(pd.DataFrame(ohlc_data))
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

        # rows = []
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

                            strategy, trade_counter = strategy.backtest(sentiment_metadata_ary)  # updates strategy.trades[] with appended trades

                            #! check here for an existing exit_date, and break if it doesn;t exist
                            if 'exit_date' in strategy.trades.columns and not strategy.trades.empty:
                                # Get the last 'exit_date' value
                                last_exit_date = strategy.trades['exit_date'].iloc[-1]
                                # Check if 'exit_date' is NaT (i.e., trade is still open)
                                if pd.isna(last_exit_date):
                                    # print(f"Trade not closed: {last_exit_date}")
                                    # The last trade has not been closed; decide to break or handle accordingly
                                    break
                                else:
                                    # The last trade has been closed; continue processing or handle as needed
                                    pass
                            else:
                                # Either 'exit_date' does not exist or there are no trades
                                # Handle accordingly, e.g., continue or break
                                print(f"No trades OR exit_date: {strategy.trades}")
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

                                if trade_counter == 0:
                                    print("No Trades!")
                                # else:
                                #     print(f"{trade_counter} trades")

                                try:
                                    t.status_line(
                                        sentiment=sentiment,
                                        trade_counter=trade_counter,
                                        rolling_window_position=rolling_window_position,
                                        negCounter=negCounter,
                                        limCounter=limCounter,
                                        conCounter=conCounter,
                                        lookCounter=lookCounter,
                                        limitCounter=line_counter,
                                        enter_date=str(strategy.trades['entry_date'].iloc[-1]),
                                    )
                                    last_trade_counter = trade_counter

                                    row = {
                                        'idx': line_counter,
                                        'FromDate': f"{strategy.trades['entry_date'].iloc[-1]}",
                                        'ToDate': f"{strategy.trades['exit_date'].iloc[-1]}",
                                        'entry_price': strategy.trades['entry_price'].iloc[-1],
                                        'exit_price': strategy.trades['exit_price'].iloc[-1],
                                        'N': negCounter,
                                        'L': limCounter,
                                        'C': conCounter,
                                        'K': lookCounter,
                                        'trx_ret': strategy.trades['trx_return'].iloc[-1],
                                        'oh_ret': strategy.trades['trx_overhodl'].iloc[-1],
                                        'entry_sentiment': strategy.trades['entry_sentiment'].iloc[-1],
                                        'exit_sentiment': strategy.trades['exit_sentiment'].iloc[-1],

                                        'cum_trx': 0.0, #strategy.trades['cum_trx'].iloc[-1],
                                        'cum_oh': 0.0, #strategy.trades['cum_oh'].iloc[-1],
                                        'cum_trx_growth': 0.0, #strategy.trades['cum_trx_growth'].iloc[-1],
                                        'cum_oh_growth': 0.0, #strategy.trades['cum_oh_growth'].iloc[-1],
                                        'cum_trx_pct': 0.0, #strategy.trades['cum_trx_pct'].iloc[-1],
                                        'cum_oh_pct': 0.0, #strategy.trades['cum_oh_pct'].iloc[-1],

                                        # 'price_change': sentiment_metadata_ary['price_change'],
                                        # 'trend': sentiment_metadata_ary['trend'],
                                        # 'average_body_size': sentiment_metadata_ary['average_body_size'],
                                        # 'average_upper_wick': sentiment_metadata_ary['average_upper_wick'],
                                        # 'average_lower_wick': sentiment_metadata_ary['average_lower_wick'],
                                        # 'volatility': sentiment_metadata_ary['volatility'],
                                    }
                                    rdf = append_dict_to_df(rdf, row)
                                except Exception as e:
                                    print(f"Error in status_line: {e}")
                                    traceback.print_exc()


                        # t.xprint(2,f"{line_counter}/({csv_lines}-{rolling_window_size})",ex=False, co=fg.GREEN)

                        if line_counter > max_loops:
                            print(f"max_loops reached: {line_counter}/{max_loops}")
                            break
                        if line_counter >= csv_lines-rolling_window_size:
                            print(f"csv_lines reached: {line_counter}/({csv_lines}-{rolling_window_size})")
                            break
                        # if line_counter > max_loops or line_counter >= csv_lines-rolling_window_size:
                            # After all data processing and just before writing to Excel
                            # do some math on the cum_return and cum_overhodl columns

                            # rdf['cum_trx'] = 1 + rdf['trx_ret']
                            # rdf['cum_trx_growth'] = 1 + rdf['cum_trx'].cumprod()
                            # rdf['cum_trx_pct'] = 1 + rdf['oh_ret']-1

rdf['cum_trx_pct'] = (1 + rdf['trx_ret']).cumprod() - 1
rdf['cum_oh_pct'] = (1 + rdf['oh_ret']).cumprod() - 1




rdf.to_excel(testvars_report_filename,index=False)

xlsx_reporter = ExcelReporter(testvars_report_filename)
xlsx_reporter.load_or_create_workbook()

xlsx_reporter.set_column_format("trx_ret", "0.00%")
xlsx_reporter.set_column_format("oh_ret", "0.00%")
xlsx_reporter.set_column_format("entry_price", "$0")
xlsx_reporter.set_column_format("exit_price", "$0")

xlsx_reporter.set_column_format("cum_trx", "0.00%")
xlsx_reporter.set_column_format("cum_oh", "0.00%")

xlsx_reporter.set_column_format("cum_trx_pct", "0.00%")
xlsx_reporter.set_column_format("cum_oh_pct", "0.00%")


# xlsx_reporter.set_column_format("price_change", "0.00%")
# xlsx_reporter.set_column_format("volatility", "0.0000")
# xlsx_reporter.set_column_format("average_body_size", "0.0000")
# xlsx_reporter.set_column_format("average_upper_wick", "0.0000")
# xlsx_reporter.set_column_format("average_lower_wick", "0.0000")
# xlsx_reporter.set_column_format("trend", "0.000")

xlsx_reporter.adjust_column_width()
xlsx_reporter.add_table()
xlsx_reporter.save()

# add additional columns here
# add a normalized value (to the cum_overhodl column) for closing price so as to compare on the chart
xlsx_reporter.add_norm_close_column(testvars_report_filename)

print(f"Results have been written to {testvars_report_filename} [{line_counter}]")
exit()


