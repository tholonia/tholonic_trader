"""
cimulator_lib.py: Utility Functions for Trading Bot

This module contains utility functions used throughout the trading bot application.
These functions provide support for data processing, formatting, and visualization.

Key Functions:
- normalize_numeric_values(values): Normalizes a list of numeric values to a 0-1 range.
- format_value(value): Formats various data types for consistent display.

Dependencies:
- colorama: For colored console output
- collections: For OrderedDict
- ExcelReporterClass: For generating Excel reports
- TholonicStrategyClass: For implementing the trading strategy
- ProfitLossPlotterClass: For plotting profit/loss data

Usage:
Import this module in other parts of the trading bot application to access
these utility functions. These functions are designed to work with the data
structures and objects used throughout the trading system.

Note: This module should be used in conjunction with other modules of the
trading bot system for full functionality.
"""

from colorama import Fore as fg, Back as bg
import pandas as pd
from collections import OrderedDict
from ExcelReporterClass import ExcelReporter
# from DataLoaderClass import DataLoader
# from TholonicStrategyClass import TholonicStrategy
# from ProfitLossPlotterClass import ProfitLossPlotter
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import csv
from pprint import pprint
import sys
import logging
import datetime
import time
# Remove all handlers associated with the root logger object.
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# Set up file handler
file_handler = logging.FileHandler('log/your_log_file.log', mode='w')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(filename)s:%(lineno)d:%(funcName)s - %(levelname)s - %(message)s'))

# Configure root logger
logging.getLogger().setLevel(logging.INFO)
logging.getLogger().addHandler(file_handler)

# Ensure no logging goes to the console
logging.getLogger().addHandler(logging.NullHandler())

def append_dict_to_df(df, data_dict):
    return pd.concat([df, pd.DataFrame([data_dict])], ignore_index=True)

def xprint(id,text,**kwargs):
    pp = kwargs.get('pp',False)
    cl = kwargs.get('co',fg.CYAN)
    ex = kwargs.get('ex',True)
    print(cl)
    print(f"-------------------------------------{id}--")
    if pp:
        pprint(text)
    else:
        print(text)
    print(f"-------------------------------------{id}--")
    print(fg.RESET)
    if ex:
        exit()

def normalize_numeric_values(values):
    numeric_values = [v for v in values if isinstance(v, (int, float))]
    if not numeric_values:
        return values  # Return original list if no numeric values

    min_val = min(numeric_values)
    max_val = max(numeric_values)

    def normalize(x):
        if isinstance(x, (int, float)):
            if max_val == min_val:
                return 1.0 if x != 0 else 0.0  # Handle case where all values are the same
            return (x - min_val) / (max_val - min_val)
        print(">>>> ",x)
        return x

    return [normalize(v) for v in values]


# def format_value(value):
#     if isinstance(value, (int, float)) and value == 0:
#         return ""
#     elif isinstance(value, float):
#         return f"{value:.6f}".rstrip('0').rstrip('.')
#     return str(value)

def format_value(value):
    """
    Format a value for display in a report.
    Returns: str: The formatted value.
    """
    if value is None:
        return ""
    elif isinstance(value, (int, float)):
        if value == 0:
            return 0  # Return 0 as a number, not an empty string
        elif isinstance(value, float):
            return round(value, 6)  # Round floats to 6 decimal places
        else:
            return value  # Return integers as is
    return str(value)  # Convert other types to string

# def adjust_column_width(ws):
#     for column in ws.columns:
#         max_length = 0
#         column_letter = get_column_letter(column[0].column)
#         for cell in column:
#             try:
#                 if len(str(cell.value)) > max_length:
#                     max_length = len(cell.value)
#             except:
#                 pass
#         adjusted_width = (max_length + 2) * 1.2
#         ws.column_dimensions[column_letter].width = adjusted_width
sCounter = 0

def print_trading_info(**kwargs):
    strategy_report_filename = kwargs.get('strategy_report_filename', 'line_results.xlsx')
    # Define the expected fields and their default values
    expected_fields = {
        'idx': 0,
        'timestamp': '',

        'sentiment': 0,
        'signal': '',
        'trading_pair': '',
        'close_price': 0,
        'last_buy_price': 0,

        'transaction_profit': 0,
        'total_profit_pct': 0,
        'HODL_units': 0,

        'order_submission_status': '',
    }

    # Update expected_fields with provided values
    for key, value in kwargs.items():
        if key in expected_fields:
            expected_fields[key] = value

    # Define all fields and the order they appear
    all_fields = OrderedDict([
        ('x', f"{expected_fields['idx']:4d}"),
        ('t', expected_fields['timestamp']),

        ('s', f"{expected_fields['sentiment']:2d}"),
        ('a', f"{expected_fields['signal']:4s}"),
        # ('Pair', expected_fields['trading_pair']),
        ('i', f"{expected_fields['last_buy_price']:10.2f}"),
        ('o', f"{expected_fields['close_price']:10.2f}"),

        # ('TxP%', expected_fields['transaction_profit']),
        ('p', f"{expected_fields['total_profit_pct']:+8.2f}%"),
        ('h', f"{expected_fields['HODL_units']:+8.4f}"),

        # ('Stat', expected_fields['order_submission_status']),


    ])

    # Prepare the output line as a list
    # output_line = list(all_fields.values())

    # Prepare the output line as a list, formatting values
    output_line = [format_value(value) for value in all_fields.values()]

    # Normalize numeric values
    # normalized_line = normalize_numeric_values(output_line)




    # Write to XLSX file
    # Use the ExcelReporter class to update the Excel file
    excel_reporter = ExcelReporter("line_results.xlsx")
    excel_reporter.update_report(output_line, list(all_fields.keys()))

    # Prepare console output
    # the following like adds titles to each value, which is cumberson
    # console_output = " | ".join(f"{key}: {format_value(value)}" for key, value in all_fields.items())
    # this output is much tigher
    console_output = ""
    for key, value in all_fields.items():
        console_output += f"| {value} "

    # Print to STDERR, which enables teh view of debug prints by using "2> /dev/null"
    if expected_fields['signal'] == "BUY":
        color = fg.RED if expected_fields['order_submission_status'] != "unavailable" else fg.LIGHTBLUE_EX
        print(color + console_output + (" unavailable" if expected_fields['order_submission_status'] == "unavailable" else "") + fg.RESET)
    elif expected_fields['signal'] == "SELL":
        print(fg.GREEN + console_output + fg.RESET + "\n", file=sys.stderr)
    else:  # HOLD
        print(fg.LIGHTMAGENTA_EX + console_output + fg.RESET, file=sys.stderr)



def calculate_average_position_price(positions):
    if not positions:
        return 0
    total_cost = sum(price * amount for price, amount in positions)
    total_amount = sum(amount for _, amount in positions)
    return total_cost / total_amount if total_amount > 0 else 0

def calculate_profit(entry_positions, exit_price, exit_amount, commission_rate):
    avg_entry_price = calculate_average_position_price(entry_positions)
    gross_profit = (exit_price - avg_entry_price) * exit_amount
    entry_commission = avg_entry_price * exit_amount * commission_rate
    exit_commission = exit_price * exit_amount * commission_rate
    net_profit = gross_profit - entry_commission - exit_commission
    total_investment = avg_entry_price * exit_amount
    net_profit_percentage = (net_profit / total_investment) * 100 if total_investment > 0 else 0
    return net_profit, net_profit_percentage

def check_stop_loss(positions, current_price, stop_loss_percentage):
    if not positions:
        return False
    avg_entry_price = calculate_average_position_price(positions)
    stop_loss_price = avg_entry_price * (1 - stop_loss_percentage)
    return current_price <= stop_loss_price

def generate_report(outputfile,trading_pair, negotiation_threshold, limitation_multiplier, contribution_threshold,
                    lookback_period, stop_loss_percentage, from_date, to_date, total_trades,
                    profitable_trades, non_profitable_trades, first_purchase_price, final_selling_price,
                    total_profit, total_profit_percentage, current_capital, last_value_in_assets_held,
                    hodl_percentage, avg_vol_price, verbosity_level, ohlcfile,action="final"):

    FCY = fg.CYAN
    FLB = fg.LIGHTBLUE_EX
    FLM = fg.LIGHTMAGENTA_EX
    FLG = fg.LIGHTGREEN_EX
    FLY = fg.LIGHTYELLOW_EX
    FLC = fg.LIGHTCYAN_EX
    FRE = fg.RED
    FYE = fg.YELLOW
    FXX = fg.RESET

    profit_ratio = profitable_trades / total_trades if total_trades > 0 else 0

    CX = trading_pair
    NT = negotiation_threshold
    LT = limitation_multiplier
    CT = contribution_threshold
    KP = lookback_period
    SL = stop_loss_percentage
    PS = f"{CX} n:{NT} l:{LT} c:{CT} k:{KP} s:{SL}{fg.RESET}"
    FR = f"{from_date}"
    TO = f"{to_date}"
    TT = total_trades
    PT = profitable_trades
    PN = non_profitable_trades
    PR = profit_ratio
    IC = first_purchase_price
    FS = final_selling_price
    TP = total_profit
    TC = total_profit_percentage
    HP = hodl_percentage
    FC = current_capital
    TR = (current_capital - first_purchase_price) / first_purchase_price * 100
    TH = last_value_in_assets_held
    HC = total_profit_percentage - hodl_percentage
    AV = avg_vol_price

    ch = {
        'CX': "trading_pair",
        'NT': "negotiation_threshold",
        'LT': "limitation_multiplier",
        'CT': "contribution_threshold",
        'KP': "lookback_period",
        'SL': "stop_loss_percentage",
        'FR': "from_date",
        'TO': "to_date",
        'TT': "total_trades",
        'PT': "profitable_trades",
        'PN': "non_profitable_trades",
        'PR': "profit_ratio",
        'IC': "first_purchase_price",
        'FS': "final_selling_price",
        'TP': "total_profit",
        'TC': "total_profit_percentage",
        'TR': "total_return",
        'BH': "buy_and_hold_return",
        'FC': "current_capital",
        'TH': "last_value_in_assets_held",
        'HP': "HOLD_percentage",
        'HC': "HODL_compare",
        'AV': "avg_vol_price",
    }

    # if verbosity_level > 0 and verbosity_level < 100:
    str = f"""
    {fg.CYAN}
    PS: Profitability Summary:         {PS}
    FR: {ch['FR']:30s} {FR}
    TO: {ch['TO']:30s} {TO}
    TT: {ch['TT']:30s} {TT}
    PT: {ch['PT']:30s} {PT}
    PN: {ch['PN']:30s} {PN}
    PR: {ch['PR']:30s} {PR}

    IC: {ch['IC']:30s} {IC}
    FS: {ch['FS']:30s} {FS}
    TP: {ch['TP']:30s} {TP}
    BH: {ch['BH']:30s} {HP}

    FC: {ch['FC']:30s} {FC}
    TR: {ch['TR']:30s} {TR}
    TH: {ch['TH']:30s} {TH}
    HP: {ch['HP']:30s} {HP}
    HC: {ch['HC']:30s} {HC}
    AV: {ch['AV']:30s} {AV}
    {fg.RESET}

    """
    print(str)

    str  = f"{FCY}{CX:10s}{FXX}"
    str += f"{FLB}n:{NT:.2f}{FXX}"
    str += F"{FLC}l:{LT:.2f}{FXX}"
    str += f"{FLM}c:{CT:.2f}{FXX}"
    str += f"{FLG}k:{KP:.2f}{FXX}"
    str += f"{FLB}s:{SL:>.1f}{FXX}"
    str += f"|{FR} - {TO}"
    str += f"|TT: {FCY}{TT:4d}{FXX}"
    str += f"|PN: {FYE}{PT:3d}/{PN:3d}{FXX}"
    str += f"|HC: {FLY}{HC:+6.2f}%{FXX}"
    str += f"|TH: {FLG}{TH:8.6f}{FXX}"
    str += f"|AV: {FLC}${AV:>12,.2f}{FXX}"


    cvsheader  = f"{ohlcfile},{ch['NT']},{ch['LT']},{ch['CT']},{ch['KP']},{ch['SL']},{ch['FR']},{ch['TO']},"
    cvsheader += f"{ch['TT']},{ch['PT']},{ch['PN']},{ch['PR']},{ch['IC']},{ch['FS']},{ch['TP']},{ch['TC']},"
    cvsheader += f"{ch['BH']},{ch['FC']},{ch['TH']},{ch['AV']},{ch['HP']},{ch['HC']}"


    csvstr  = f"{ohlcfile},{NT},{LT},{CT},{KP},{SL},{FR},{TO},"
    csvstr += f"{TT},{PT},{PN},{PR},{IC},{FS},{TP},{TC},"
    csvstr += f"{HP},{FC},{TH},{AV},{HP},{HC}"

    with open(outputfile,"w") as f:
        f.write(cvsheader+"\n")
        f.write(csvstr+"\n")

def print_colored(text, color):
    """
    Print text in the specified color.
    Returns:    None
    """
    print(color + text + fg.RESET)

def format_number(number, decimals=2):
    """
    Format a number to a specified number of decimal places.
    Returns: str: The formatted number as a string.
    """
    return f"{number:.{decimals}f}"

def calculate_percentage(part, whole):
    """
    Calculate the percentage of a part relative to a whole.
    Returns:float: The calculated percentage.
    """
    return (part / whole) * 100 if whole != 0 else 0

def parse_date(date_string):
    """
    Parse a date string into a datetime object.
    Returns: datetime: The parsed datetime object.
    """
    return datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")

def calculate_time_difference(start_date, end_date):
    """
    Calculate the time difference between two dates.
    Returns: timedelta: The time difference.
    """
    return end_date - start_date

def print_testvarsusage():
    str = f"""
    Usage: python testvars_fast.py -c <configfile> | -h for help
    """
    print(str)

def limit_decimals(number, decimals=2):
    """
    Limit the number of decimal places in a number.
    Returns: float: The number with the specified number of decimal places.
    """
    return float(Decimal(str(number)).quantize(Decimal(f"0.{'0'*decimals}"), rounding=ROUND_HALF_UP))

def count_csv_lines(file_path):
    """
    Count the number of lines in a CSV file.
    Returns: int: The number of lines in the CSV file.
    """
    with open(file_path, 'r') as file:
        return sum(1 for row in csv.reader(file))

def datetime_to_unix(date_string):
    # Parse the date string manually
    year, month, day, hour, minute, second = map(int, date_string.replace(' ', '-').replace(':', '-').split('-'))
    dt = datetime(year, month, day, hour, minute, second)

    # Convert datetime object to Unix timestamp
    return dt.timestamp()

def unix_to_datetime(unix_timestamp):
    """Convert Unix timestamp to datetime string."""
    return datetime.fromtimestamp(unix_timestamp).strftime('%Y-%m-%d %H:%M:%S')


def pandas_timestamp_to_python_timestamp(pandas_ts):
    """
    Convert a pandas Timestamp to a Python timestamp (Unix timestamp as a float).

    :param pandas_ts: pandas.Timestamp
    :return: float
    """
    return pandas_ts.timestamp()

def pandas_timestamp_to_unix(pandas_ts):
    """
    Convert a pandas Timestamp to a Unix timestamp (float).

    :param pandas_ts: pandas._libs.tslibs.timestamps.Timestamp
    :return: float
    """
    return pandas_ts.timestamp()

def status_line(**kwargs):
    sentiment = kwargs.get('sentiment', 0)
    trade_counter = kwargs.get('trade_counter', 0)
    rolling_window_position = kwargs.get('rolling_window_position', 0)
    negCounter = kwargs.get('negCounter', 0)
    limCounter = kwargs.get('limCounter', 0)
    conCounter = kwargs.get('conCounter', 0)
    lookCounter = kwargs.get('lookCounter', 0)
    limitCounter = kwargs.get('limitCounter', 0)
    enter_date = kwargs.get('enter_date', 'missing-date')

    status_line = f"[{enter_date}]  L:{limitCounter:6d} S:{sentiment:2d} T:{trade_counter:6d}: W:{rolling_window_position:.0f}  \tn:{fg.LIGHTCYAN_EX}{negCounter:.2f}{fg.RESET}\tl:{fg.LIGHTMAGENTA_EX}{limCounter:.2f}{fg.RESET}\tc:{fg.LIGHTGREEN_EX}{conCounter:.2f}{fg.RESET}\tk:{fg.LIGHTRED_EX}{lookCounter:.0f}{fg.RESET}                "
    print(status_line, file=sys.stderr, end="\n",flush=True)

def ts2str(ts):
    dt_object = datetime.datetime.fromtimestamp(ts)

    # Format the datetime object to a string (month day, year hour:minute:second)
    formatted_time = dt_object.strftime("%B %d, %Y %H:%M:%S")
    return formatted_time

def str2ts(time_string):
    # Parse the time string into a datetime object
    dt_object = datetime.datetime.strptime(time_string, "%B %d %Y %H:%M:%S")

    # Convert the datetime object to a UNIX timestamp
    unix_timestamp = time.mktime(dt_object.timetuple())

    return unix_timestamp

FCY = fg.CYAN
FLB = fg.LIGHTBLUE_EX
FLM = fg.LIGHTMAGENTA_EX
FLG = fg.LIGHTGREEN_EX
FLY = fg.LIGHTYELLOW_EX
FLC = fg.LIGHTCYAN_EX
FRE = fg.RED
FYE = fg.YELLOW
FXX = fg.RESET

