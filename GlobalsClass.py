"""
GlobalsClass.py: Global Variables and Data Structures for Trading Bot

This module contains global variables and data structures used throughout the trading bot application.
These variables are used to track trading activity, maintain state, and store historical data.

Key Variables:
- last_buy_date_list: List of datetime objects representing the last buy dates.
- last_sell_date_list: List of datetime objects representing the last sell dates.
- last_buy_price_list: List of prices at which the last buys occurred.
- positions: Integer representing the current number of open positions.
- trades_list: List to store all executed trades.
- trade_counter: Integer counter for the total number of trades executed.
- cum_return: Float representing the cumulative return of all trades.
- cum_overhodl: Float representing the cumulative over-hold performance.

Usage:
Import this module in other parts of the trading bot application to access
these global variables. These variables are designed to be modified and
accessed throughout the trading process to maintain the overall state of
the trading system.

Note: Be cautious when modifying these variables, as they affect the entire
trading system's state. Proper synchronization mechanisms should be used
when accessing these variables in a multi-threaded environment.
"""


import pandas as pd
import datetime

last_buy_date_list = [datetime.datetime.fromtimestamp(0.0)]
last_sell_date_list = [datetime.datetime.fromtimestamp(0.0)]
last_buy_price_list = []
positions = 0
trades_list = []
trade_counter = 0
cum_return_pct = 0
cum_overhodl = 0

running_trx_return_pct = [0]
running_trx_overhodl_pct = [0]

capital = 0
