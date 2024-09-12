#!/usr/bin/env python
"""
trade_bot.py: Main Trading Bot Script

This script serves as the main entry point for the trading bot application.
It integrates various components and strategies to execute trading operations.

Key Features:
1. Command-line interface for configuring trading parameters
2. Integration with TholonicStrategy for trading decisions
3. Support for both live trading and backtesting modes
4. Profit/loss tracking and reporting
5. Customizable trading pair, position limits, and thresholds

Dependencies:
- numpy: For numerical operations
- colorama: For colored console output
- TholonicStrategyClass: For implementing the trading strategy
- ProfitLossPlotterClass: For visualizing profit/loss data
- trade_bot_lib: Custom library with utility functions

Usage:
Run this script from the command line with various options to configure
the trading bot's behavior. Use -h or --help for a full list of options.

Example:
    python trade_bot.py -p BTCUSD -b -m 5 -n 0.3 -l 0.25 -c 2.0 -k 20

Note: Ensure all dependencies are installed and properly configured before
running this script. Refer to the project documentation for setup instructions.
"""

import sys
import numpy as np
import os
import getopt
from datetime import datetime
import re
import traceback
import time
import trade_bot_lib as t
from pprint import pprint
from TholonicStrategyClass import TholonicStrategy
from ProfitLossPlotterClass import ProfitLossPlotter
from DataLoaderClass import DataLoader
from SentimentClass import OHLCSentimentAnalyzer

import yaml

from colorama import (
    Fore as fg,
    Back as bg,
    Style as st
    )
FCY = fg.CYAN
FLB = fg.LIGHTBLUE_EX
FLM = fg.LIGHTMAGENTA_EX
FLG = fg.LIGHTGREEN_EX
FLY = fg.LIGHTYELLOW_EX
FLC = fg.LIGHTCYAN_EX
FRE = fg.RED
FYE = fg.YELLOW
FXX = fg.RESET


from trade_bot_lib import (
    calculate_average_position_price,
    calculate_profit,
    check_stop_loss,
    print_trading_info,
    generate_report,
)
import trade_bot_lib as t

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
    """
    print(str)
    exit()


def dynamic_assign(x):
    # Define ranges and corresponding Y and Z and W values
    # Each tuple contains (low, high, y, z, w)
    ranges = [
        (-1.000,-0.666, 0.3, 0.3, 0.3),
        (-0.666,-0.333, 0.5, 0.5, 0.5),
        (-0.333,+0.333, 0.7, 0.7, 0.7),
        (+0.333,+0.666, 0.9, 0.9, 0.9),
        (+0.666,+1.000, 0.1, 0.1, 0.1)
    ]


    # Loop through the ranges to find the correct one
    for low, high, y, z, w in ranges:
        if low <= x < high:
            return y, z, w

    # If no range is found (shouldn't happen with our setup)
    return None, None, None



#!┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
#!┃ main                                                                    ┃
#!┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛


def main(argv):

    # Load configuration from YAML file
    with open('config.yaml', 'r') as config_file: config = yaml.safe_load(config_file)

    # Extract variables for testvars_fast from the config
    C = config['testvars_fast']

    from_date = C['from_date']
    to_date = C['to_date']
    trading_pair = C['trading_pair']
    livemode = C['livemode']
    max_positions = C['max_positions']
    commission_rate = C['commission_rate']
    initial_balance = C['initial_balance']
    verbosity_level = C['verbosity_level']
    limitcount = C['limitcount']
    stop_loss_percentage = C['stop_loss_percentage']
    ohlcfile=C['csv_file']



    # negotiation_threshold=negotiation_threshold,
    # limitation_multiplier=limitation_multiplier,
    # contribution_threshold=contribution_threshold,
    # lookback_period=lookback_period,



    value_in_assets_held = 0

    #! ideal for BTCUSD1h candles for 2024-07-27 - 2024-08-27 KRAKEN
    # negotiation_threshold = 0.5
    # limitation_multiplier = 0.3
    # contribution_threshold = 1.4
    # lookback_period = 15
    # stop_loss_percentage = 4.8 # 1%

    #! ideal for BTCUSD 1h candles for 2023-07-27 - 2024-08-27 COINBASE
    negotiation_threshold = 1.3
    limitation_multiplier = 0.6
    contribution_threshold = 2.4
    lookback_period = 16

    try:
        opts, args = getopt.getopt(argv, "hp:bm:n:l:c:k:r:s:i:v:L:F:R:",
                                   ["help", "pair=", "livemode", "max-positions=", "negotiation=",
                                    "limitation=", "contribution=", "lookback=", "commission=",
                                    "stop-loss=", "initial-balance=", "verbosity=","limitcount=",
                                    "ohlcfile=","daterange="])
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
            stop_loss_percentage = float(arg)
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





    stop_loss_decimal = stop_loss_percentage / 100
    if verbosity_level > 2 and verbosity_level < 100 or verbosity_level == 101:
        plotting_enabled = True
    else:
        plotting_enabled = False

    livemode_idx_iter = 0
    previous_time = ""
    write_cvs_header_once = True

    # Position tracking
    current_positions = []
    total_profit = 0
    total_profit_percentage = 0
    long_positions = False
    num_positions = 0

    # Price tracking
    first_purchase_price = None
    final_selling_price = 0
    last_value_in_assets_held = 0
    hodl_percentage = 0
    last_buy_price = 0
    # last_buy_macd_sentiment = 0

    # Profitability tracking
    profitable_trades = 0
    non_profitable_trades = 0

    # Buy-and-hold tracking
    initial_price = None
    avg_position_price = None

    # Initialize the profit/loss plotter
    if plotting_enabled:
        plotter = ProfitLossPlotter()

    # Initialize current_capital to None, we'll set it on the first purchase
    current_capital = None

    # Convert date strings to datetime objects
    from_date_dt = datetime.strptime(from_date, "%Y-%m-%d %H:%M:%S")
    to_date_dt = datetime.strptime(to_date, "%Y-%m-%d %H:%M:%S")

    # get rid of the old line_results.xlsx file if it exists
    if os.path.exists("line_results.xlsx"):
       os.remove("line_results.xlsx")





    while True: #! this is the main loop that runs the strategy
        loopRange = int((t.count_csv_lines(ohlcfile)-1)/ lookback_period)
        for rolling_window_position in range(loopRange):
            loader = DataLoader(ohlcfile, from_date, to_date, lookback_period)
            loader.shift_window(rolling_window_position)
            ohlc_data = loader.get_data()

            # sentiment_analyzer = OHLCSentimentAnalyzer(apiout)



            order_submission_status = ""
            try:

                strategy = TholonicStrategy(
                    trading_pair=trading_pair,
                    negotiation_threshold=1,
                    limitation_multiplier=1,
                    contribution_threshold=1,
                    lookback_period=lookback_period,
                    livemode=livemode,
                    livemode_n_elements=livemode_idx_iter+lookback_period,
                    # ohlcfile=ohlcfile,
                    # from_date=from_date,
                    # to_date=to_date,
                    ohlc_data=ohlc_data,
                )
                latest_data, strategy.data = strategy.run_strategy()


                # t.xprint(type(latest_data))



                avg_volume = latest_data['average_volume']
                # signal = strategy.generate_signals()

                current_time = f"{latest_data.name}"  # CONVER TO STR
                current_time_dt = datetime.strptime(current_time, "%Y-%m-%d %H:%M:%S")
                current_price = latest_data['close']
                in_date_range = from_date_dt <= current_time_dt <= to_date_dt
                available_positions = max_positions - len(current_positions)
                livemode_idx_iter += 1

                # Break when we get to the last date or we read the same record twice or hit the count limit
                if current_time_dt > to_date_dt or current_time == previous_time or livemode_idx_iter > limitcount:
                    if current_time_dt > to_date_dt:
                        print(fg.LIGHTYELLOW_EX + f"Reached end date: {to_date_dt}" + fg.RESET)
                    if current_time == previous_time:
                        print(fg.LIGHTYELLOW_EX + f"Reached same record twice as record {livemode_idx_iter}: {current_time}" + fg.RESET)
                    if livemode_idx_iter > limitcount:
                        print(fg.LIGHTYELLOW_EX + f"Reached limitcount: {limitcount}" + fg.RESET)
                    exit()
                previous_time = current_time

                # Check for stop loss
                if check_stop_loss(current_positions, current_price, stop_loss_decimal):
                    signal = "SELL"
                    if verbosity_level > 1 and verbosity_level < 100:
                        print(fg.LIGHTYELLOW_EX + f"Stop loss ({stop_loss_percentage:.2f}%) triggered at {current_price:.2f}" + fg.RESET,file=sys.stderr)


                #!┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
                #!┃ BUY                                                                     ┃
                #!┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                # Position management
                if strategy.data['buy_condition'].iloc[-1] == True:

                    if (
                        available_positions > 0 and
                        in_date_range
                        # latest_data['macd_sentiment'] < -0.8

                        ):
                        #! and latest_data['volatility'] < 1000:


                        # print(f"\tMACD Signal: {latest_data['macd_signal']}")
                        # print(f"\tVolatility: {latest_data['volatility']}")
                        # print(f"\tAverage Volatility: {latest_data['average_volatility']}")
                        # print(f"\tVR: {latest_data['average_volume']/latest_data['volatility']}")

                        if initial_price is None:
                            initial_price = current_price

                        if first_purchase_price is None:
                            first_purchase_price = current_price
                            current_capital = first_purchase_price

                        # Calculate the investment amount for this position.
                        # Divide the current capital by the remaining available positions.
                        # This ensures equal distribution of capital across all potential positions.
                        investment_amount = current_capital / (max_positions - num_positions)

                        # Calculate the number of units to buy based on the investment amount and current price
                        units_to_buy = investment_amount / current_price

                        # save the buy price.  Should be average buy price if we are averaging
                        last_buy_price = current_price

                        # Append the current price and the calculated units to the current positions list
                        current_positions.append((current_price, units_to_buy))

                        # Add the units to the total units held
                        value_in_assets_held += units_to_buy
                        last_value_in_assets_held = value_in_assets_held

                        # Set the long_positions flag to True
                        long_positions = True

                        # Calculate the average position price
                        avg_position_price = calculate_average_position_price(current_positions)

                        # Add to "Individual Trade Porfits/Losses" to the plotter
                        if plotting_enabled:
                            plotter.add_trade(current_time, 0, current_price, 'BUY', available_positions = available_positions)


                        if verbosity_level > 1 and verbosity_level < 100:
                            print_trading_info(
                                idx                 =livemode_idx_iter,
                                timestamp           =current_time,
                                signal              =signal,
                                trading_pair        =trading_pair,
                                close_price         =current_price,
                                # last_buy_macd_sentiment = last_buy_macd_sentiment,
                                # macd_sentiment      =latest_data['macd_sentiment'],
                                # normalized_macd_sentiment      =latest_data['normalized_macd_sentiment'],

                                #
                                # volatility          =latest_data['volatility'],
                                # average_volatility  =latest_data['average_volatility'],
                                # volume              =latest_data['volume'],
                                # average_volume      =latest_data['average_volume'],

                                # macd_sig            =latest_data['macd_signal'],
                                # macd                =latest_data['macd'],
                                # macd_sigline        =latest_data['macd_signal_line'],

                                order_submission_status=order_submission_status,

                                # HODL_units  =value_in_assets_held,
                                # long_positions    =long_positions,
                                # avg_position_price  =avg_position_price,
                                # total_profit        =total_profit,
                                # total_profit_pct    =total_profit_percentage,
                                # num_positions       =num_positions,

                            )
                        # try:
                        #     last_buy_macd_sentiment = latest_data['macd_sentiment']
                        # except Exception as e:
                        #     last_buy_macd_sentiment = 0
                    else:
                        order_submission_status = "unavailable"

                #~┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
                #~┃ SELL                                                                    ┃
                #~┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                # Handling the SELL signal when there are open positions

                # if strategy.data['sell_condition'].iloc[-1] == True:
                if strategy.data['sell_condition'].iloc[-1] == True and current_positions and in_date_range:
                    #!and latest_data['macd_sentiment'] - last_buy_macd_sentiment > 0:
                    #!and latest_data['macd_sentiment'] >= 0.5:
                    #! and latest_data['volatility'] >= 1000: # and total_units_held > 0:

                    # macds_delta = latest_data['macd_sentiment'] - last_buy_macd_sentiment
                    # print(f">>>> macds_delta: {macds_delta}")


                    volatility = latest_data['volatility']
                    average_volatility = latest_data['average_volatility']

                    # Calculate the profit for closing all positions at the current price, including commission
                    total_amount = sum(amount for _, amount in current_positions)
                    profit, profit_percentage = calculate_profit(current_positions, current_price, total_amount, commission_rate)

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
                    value_in_assets_held = total_profit/current_price

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
                    if plotting_enabled:
                        plotter.add_trade(current_time, profit, current_price, 'SELL',available_positions=available_positions)


                    if verbosity_level > 1 and verbosity_level < 100:
                        # basic print-to-screen output for each transaction
                        print_trading_info(
                            idx                 =livemode_idx_iter,
                            timestamp           =current_time,
                            signal              =signal,
                            trading_pair        =trading_pair,
                            close_price         =current_price,
                            last_buy_price      =last_buy_price,
                            #
                            transaction_profit  =transaction_profit,
                            total_profit_pct    =total_profit_percentage,
                            HODL_units          =value_in_assets_held,
                            # macd_sentiment      =latest_data['macd_sentiment'],
                            # last_buy_macd_sentiment = last_buy_macd_sentiment,
                            # macds_delta = macds_delta,

                            # normalized_macd_sentiment      =latest_data['normalized_macd_sentiment'],
                            #
                            # volume              =latest_data['volume'],
                            # average_volume      =latest_data['average_volume'],
                            # volatility          =volatility,
                            # average_volatility  =average_volatility,
                            # #
                            # macd_sig            =latest_data['macd_signal'],
                            # macd                =latest_data['macd'],
                            # macd_sigline        =latest_data['macd_signal_line'],
                            #
                            order_submission_status=order_submission_status,

                            # avg_position_price=0, # avg_position_price is 0 after selling
                            # total_profit=total_profit,
                            # num_positions=num_positions ,

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
                    if plotting_enabled:
                        plotter.add_trade(current_time, 0, current_price, signal, volatility, average_volatility)

                #TODO create a generate_line_report for each transaction
                # generate_report("line_results.csv",
                #     trading_pair, negotiation_threshold, limitation_multiplier, contribution_threshold,
                #     lookback_period, stop_loss_percentage, from_date, to_date, 0,
                #     profitable_trades, non_profitable_trades, first_purchase_price, final_selling_price,
                #     total_profit, total_profit_percentage, current_capital, last_value_in_assets_held,
                #     hodl_percentage, 0, verbosity_level, ohlcfile, "line"
                # )

                time.sleep(0.0)  # Wait before next update

            except KeyboardInterrupt:
                print("Strategy stopped by user.")
                break
            except Exception as e:
                print(f"An error occurred: {e}")
                traceback.print_exc()
                exit()

    # end of while loop

    # Calculate and print profitability ratio
    total_trades = profitable_trades + non_profitable_trades
    print("total_trades",total_trades)
    if total_trades > 0:
        hodl_percentage = (final_selling_price - initial_price) / initial_price * 100
        avg_vol_price = avg_volume * final_selling_price

        print("CALLING generate_report>>>",write_cvs_header_once)

        # if verbosity_level == 101:

        generate_report("final_results.csv",
            trading_pair, negotiation_threshold, limitation_multiplier, contribution_threshold,
            lookback_period, stop_loss_percentage, from_date, to_date, total_trades,
            profitable_trades, non_profitable_trades, first_purchase_price, final_selling_price,
            total_profit, total_profit_percentage, current_capital, last_value_in_assets_held,
            hodl_percentage, avg_vol_price, verbosity_level, ohlcfile, "final"
        )
    else:
        print(fg.LIGHTCYAN_EX + f"\nNo trades were executed during the livemode." + fg.RESET)

    # Plot the profits and losses
    if plotting_enabled:
        plotter.plot(
            first_purchase_price,
            negotiation_threshold,
            limitation_multiplier,
            contribution_threshold,
            lookback_period,
            volatility,
            verbosity_level,
            stop_loss_percentage,
            ohlcfile,
            total_profit_percentage,
            hodl_percentage,
        )

if __name__ == "__main__":
    main(sys.argv[1:])