#!/usr/bin/env python

import pandas as pd
import numpy as np
import getopt
import sys
from collections import deque
from colorama import Fore as fg
from SentimentClass import OHLCSentimentAnalyzer

# def analyze_ohlc_sentiment(data):
#     """
#     Analyze sentiment of OHLC data for a given window.

#     :param data: pandas DataFrame with 'Open', 'High', 'Low', 'Close' columns
#     :return: sentiment label for the given window
#     """
#     opens = data['Open']
#     closes = data['Close']
#     highs = data['High']
#     lows = data['Low']

#     price_change = (closes.iloc[-1] - opens.iloc[0]) / opens.iloc[0]
#     volatility = (highs.max() - lows.min()) / opens.iloc[0]
#     trend = np.polyfit(range(len(closes)), closes, 1)[0]

#     # Calculate additional metrics
#     body_sizes = abs(closes - opens) / opens
#     average_body_size = body_sizes.mean()
#     upper_wicks = (highs - np.maximum(opens, closes)) / opens
#     lower_wicks = (np.minimum(opens, closes) - lows) / opens
#     average_upper_wick = upper_wicks.mean()
#     average_lower_wick = lower_wicks.mean()


#     Strong_Bear         = ["Strong Bear",       "🡳",fg.LIGHTRED_EX]
#     Bear                = ["Bear",              "🡦",fg.RED]
#     Sideways            = ["Sideways",          "🡒",fg.WHITE]
#     Bull                = ["Bull",              "🡥",fg.GREEN]
#     Strong_Bull         = ["Strong Bull",       "🡹",fg.LIGHTGREEN_EX]

#     Strong_Resistance   = ["Strong Resistance", "⊢",fg.LIGHTCYAN_EX]
#     Strong_Support      = ["Strong Support",    "⊥",fg.LIGHTYELLOW_EX]
#     High_Volatility     = ["High Volatility",   "≋",fg.LIGHTMAGENTA_EX]
#     Mixed               = ["Mixed",             "⥯",fg.LIGHTYELLOW_EX]


#     if abs(price_change) < 0.01 and volatility < 0.02: return Sideways
#     elif price_change < -0.05 and trend < 0: return Strong_Bear
#     elif price_change < -0.02 and trend < 0: return Bear
#     elif price_change > 0.05 and trend > 0: return Strong_Bull
#     elif price_change > 0.02 and trend > 0: return Bull
#     elif average_upper_wick > 2 * average_body_size: return Strong_Resistance
#     elif average_lower_wick > 2 * average_body_size: return Strong_Support
#     elif volatility > 0.04: return High_Volatility
#     else: return Mixed

def load_and_analyze_ohlc_data(file_path, omask,analyzer,window_size=16):
    # Create a deque to act as a sliding window
    window = deque(maxlen=window_size)

    # Open the CSV file and read it line by line
    with open(file_path, 'r') as file:
        # Read the header
        header = next(file).strip().split(',')

        # Find the indices of required columns
        timestamp_idx = header.index('timestamp')
        open_idx = header.index('open')
        high_idx = header.index('high')
        low_idx = header.index('low')
        close_idx = header.index('close')
        volume_idx = header.index('volume')

        counter = 0

        # Process each line
        for line_num, line in enumerate(file, start=1):
            data = line.strip().split(',')

            # Extract required data
            timestamp = pd.to_datetime(data[timestamp_idx])
            ohlc_data = {
                'timestamp': timestamp,
                'open': float(data[open_idx]),
                'high': float(data[high_idx]),
                'low': float(data[low_idx]),
                'close': float(data[close_idx]),
                'volume': float(data[volume_idx]),
            }

            # Add to the window
            window.append(ohlc_data)

            # If the window is full, analyze sentiment
            if len(window) == window_size:
                df_window = pd.DataFrame(list(window))
                s = analyzer.analyze(df_window)

                # Print the result
                # print(f"Window ending at line {line_num}:")
                # print(f"Start: {window[0]['timestamp']}, End: {window[-1]['timestamp']}")
                # print(f"Sentiment: {sentiment}")

                ostr = ""
                mname = ''
                msymbol = ''
                mcolor = ''
                mnewline = ''

                if omask & 1 == 1: mname = s[0]
                if omask & 2 == 2: msymbol = s[1]
                if omask & 4 == 4: mcolor = s[2]
                if omask & 8 == 8: mnewline = "\n"

                # print(f"|{mcolor}|{mname}|{msymbol}|{mnewline}|")
                # exit()


                ostr = f"{mcolor}{mname} {msymbol}"
                print(ostr,flush=True,end=mnewline)
                counter += 1
                if counter == 168:
                    print( "")
                    counter = 0
                # print("---")

        # print(f"Total lines processed: {line_num}")

def decbinary(decimal_num, min_length=4):
    if decimal_num == 0:
        return [0] * min_length

    binary = []
    while decimal_num > 0:
        binary.insert(0, decimal_num % 2)
        decimal_num //= 2

    # Pad with zeros if the array is shorter than min_length
    while len(binary) < min_length:
        binary.insert(0, 0)

    return binary

def showhelp():
    print("help")
    rs = """
    -h, --help          show help
    -f, --csvfile       filename
    -o, --omask         1-15

output mask:
     0  000  blank                              blank
     1  001  name                               contiguous monocolor words
     2  010  symbol                             contiguous monocolor symbols
     3  011  name + symbol                      contiguous monocolor words and symbols
     4  100  color                              blank
     5  101  color + symbol                     contiguous color words
     6  110  color + name                     * contiguous color symbols
     7  111  color + name + symbol              contiguous color words and symbols
     8 1000 newlines                            blank
     9 1001 newlines + name                     monocolor words with newlines
    10 1010 newlines + symbol                   monocolor symbols with newlines
    11 1011 newlines + name + symbol            monocolor words and symbols with newlines
    12 1100 newlines + color                    blank
    13 1101 newlines + color + symbol           color words with newlines
    14 1110 newlines + color + name             color symbols with newlines
    15 1111 newlines + color + name + symbol  * color words and symbols with newlines (default)

in contriguious mode, a newline is added ever 168 symbols, which equals 1 week of 1hr data


"""
    print(rs)
    exit()

filename = 'data/latest_coinbase.csv'
omask = 15


argv = sys.argv[1:]

try:
    opts, args = getopt.getopt(argv, "hf:o:", ["help", "filename=", "omask="])
except Exception as e:
    print(str(e))

for opt, arg in opts:
    if opt in ("-h", "--help"):
        showhelp()
    if opt in ("-f", "--filename"):
        filename = arg
    if opt in ("-o", "--omask"):
        omask = int(arg)


# exit()
apiout = False # return full result list, not the API number-only value

analyzer = OHLCSentimentAnalyzer(apiout)
load_and_analyze_ohlc_data(filename,omask,analyzer)