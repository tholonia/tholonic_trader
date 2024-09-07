"""
trade_bot_vars.py: Global Variables for Trading Bot

This module contains global variables used throughout the trading bot application.
These variables are used for various purposes including reporting, data management,
and strategy implementation.

Key Variables:
- line_report_header_write_buy_once: Flag to ensure buy report header is written only once
- line_report_header_write_sell_once: Flag to ensure sell report header is written only once
- line_report_header_write_once: Flag to ensure general report header is written only once
- ohlc_ary: Storage for OHLC (Open, High, Low, Close) data
- snt: Dictionary mapping sentiment codes to their string representations
- report_line: String to store the current report line
- rolling_window_position: Position of the current rolling window in data analysis
- position: Current trading position

Usage:
Import this module in other parts of the trading bot application to access
these global variables. Ensure to modify these variables carefully as they
affect the overall behavior of the trading system.

Note: This module should be used in conjunction with other modules of the
trading bot system for full functionality.
"""

line_report_header_write_buy_once = True
line_report_header_write_sell_once = True
line_report_header_write_once = True
ohlc_ary = False

snt = {
    1: "Sideways",
    2: "Strong Bear",
    3: "Bear",
    4: "Strong Bull",
    5: "Bull",
    6: "Strong Resistance",
    7: "Strong Support",
    8: "High Volatility",
    9: "Neutral",
    10: "Mixed",
}

report_line = ""
rolling_window_position = 0
position = 0