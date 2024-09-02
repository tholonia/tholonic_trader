#!/usr/bin/env python
import sys
import getopt
from datetime import datetime
import re
import traceback
import time
import trade_bot_lib as t

from colorama import Fore as fg, Back as bg, Style as st
from trade_bot_lib import (
    DataLoader,
    TholonicStrategy,
    ProfitLossPlotter,
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

def main(argv):

    FCY = fg.CYAN
    FLB = fg.LIGHTBLUE_EX
    FLM = fg.LIGHTMAGENTA_EX
    FLG = fg.LIGHTGREEN_EX
    FLY = fg.LIGHTYELLOW_EX
    FLC = fg.LIGHTCYAN_EX
    FRE = fg.RED
    FYE = fg.YELLOW
    FXX = fg.RESET

    trading_pair = "BTCUSD"
    livemode = False
    max_positions = 1
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
    stop_loss_percentage = 4.8 # 1%




    commission_rate = 0.001 # 0.1%
    initial_balance = 1000 # this never gets used as we use the first price as a initial balance
    verbosity_level = 0
    limitcount = 720
    ohlcfile = False #"data//BTCUSD_OHLC_1440_default.csv"
    from_date = False #"2016-12-10"
    to_date = False #"2017-12-16"


    value_in_assets_held = 0



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

    while True: #! this is the main loop that runs the strategy
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

            avg_volume = latest_data['average_volume']
            livemode_idx_iter += 1
            signal = strategy.get_signal()
            current_time = f"{latest_data.name}"  # CONVER TO STR
            current_time_dt = datetime.strptime(current_time, "%Y-%m-%d %H:%M:%S")
            current_price = latest_data['close']
            in_date_range = from_date_dt <= current_time_dt <= to_date_dt
            available_positions = max_positions - len(current_positions)

            # Break when we get to the last date or we read teh same record twice or hit the count limit
            if current_time_dt > to_date_dt or current_time == previous_time or livemode_idx_iter > limitcount:
                if current_time_dt > to_date_dt:
                    print(fg.LIGHTYELLOW_EX + f"Reached end date: {to_date_dt}" + fg.RESET)
                if current_time == previous_time:
                    print(fg.LIGHTYELLOW_EX + f"Reached same record twice as record {livemode_idx_iter}: {current_time}" + fg.RESET)
                if livemode_idx_iter > limitcount:
                    print(fg.LIGHTYELLOW_EX + f"Reached limitcount: {limitcount}" + fg.RESET)
                break
            previous_time = current_time

            # Check for stop loss
            if check_stop_loss(current_positions, current_price, stop_loss_decimal):
                signal = "SELL"
                if verbosity_level > 1 and verbosity_level < 100:
                    print(fg.LIGHTYELLOW_EX + f"Stop loss ({stop_loss_percentage:.2f}%) triggered at {current_price:.2f}" + fg.RESET)

            # Position management
            if signal == "BUY":
                if available_positions > 0 and in_date_range: #! and latest_data['volatility'] < 1000:
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
                            value_in_assets_held,
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
                value_in_assets_held = 0

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
                        value_in_assets_held,
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
                if plotting_enabled:
                    plotter.add_trade(current_time, 0, current_price, signal, volatility, average_volatility)

            time.sleep(0.0)  # Wait before next update

        except KeyboardInterrupt:
            print("Strategy stopped by user.")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()
            exit()

    # Calculate and print profitability ratio
    total_trades = profitable_trades + non_profitable_trades
        # Calculate and print profitability ratio
    total_trades = profitable_trades + non_profitable_trades
    if total_trades > 0:
        hodl_percentage = (final_selling_price - initial_price) / initial_price * 100
        avg_vol_price = avg_volume * final_selling_price

        write_cvs_header_once = generate_report(
            trading_pair, negotiation_threshold, limitation_multiplier, contribution_threshold,
            lookback_period, stop_loss_percentage, from_date, to_date, total_trades,
            profitable_trades, non_profitable_trades, first_purchase_price, final_selling_price,
            total_profit, total_profit_percentage, current_capital, last_value_in_assets_held,
            hodl_percentage, avg_vol_price, verbosity_level, ohlcfile, write_cvs_header_once
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