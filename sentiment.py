#!/usr/bin/env python
"""
sentiment.py: OHLC Data Sentiment Analysis

This module provides functionality for analyzing the sentiment of OHLC (Open, High, Low, Close)
financial data. It includes methods to categorize market sentiment based on various price action
indicators over a specified time window.

Key Features:
1. Sentiment analysis of OHLC data over a sliding window
2. Categorization of market sentiment (e.g., Bullish, Bearish, Sideways)
3. Calculation of price trends, volatility, and candlestick characteristics

Main Function:
- analyze_ohlc_sentiment: Analyzes OHLC data and returns sentiment labels

Dependencies:
- pandas: For data manipulation and analysis
- numpy: For numerical operations

Usage:
Import this module in other parts of the trading bot application to perform
sentiment analysis on OHLC data. The sentiment analysis can be used to inform
trading decisions or to provide market insights.

Note: This module should be used in conjunction with other modules of the
trading bot system for comprehensive market analysis and decision-making.
"""

import pandas as pd
import numpy as np

def analyze_ohlc_sentiment(data, window_size=16):
    """
    Analyze sentiment of OHLC data over a given window size.

    :param data: pandas DataFrame with 'Open', 'High', 'Low', 'Close' columns
    :param window_size: int, number of periods to consider for each sentiment analysis
    :return: list of sentiment labels for each window
    """
    def categorize_sentiment(window):
        opens = window['Open']
        closes = window['Close']
        highs = window['High']
        lows = window['Low']

        price_change = (closes.iloc[-1] - opens.iloc[0]) / opens.iloc[0]
        volatility = (highs.max() - lows.min()) / opens.iloc[0]
        trend = np.polyfit(range(len(closes)), closes, 1)[0]

        # Calculate additional metrics
        body_sizes = abs(closes - opens) / opens
        average_body_size = body_sizes.mean()
        upper_wicks = (highs - np.maximum(opens, closes)) / opens
        lower_wicks = (np.minimum(opens, closes) - lows) / opens
        average_upper_wick = upper_wicks.mean()
        average_lower_wick = lower_wicks.mean()

        if abs(price_change) < 0.01 and volatility < 0.02:
            return "Sideways"
        elif price_change < -0.05 and trend < 0:
            return "Strong Bear"
        elif price_change < -0.02 and trend < 0:
            return "Bear"
        elif price_change > 0.05 and trend > 0:
            return "Strong Bull"
        elif price_change > 0.02 and trend > 0:
            return "Bull"
        elif average_upper_wick > 2 * average_body_size:
            return "Strong Resistance"
        elif average_lower_wick > 2 * average_body_size:
            return "Strong Support"
        elif volatility > 0.04:
            return "High Volatility"
        else:
            return "Mixed"

    sentiments = []
    for i in range(len(data) - window_size + 1):
        window = data.iloc[i:i+window_size]
        sentiment = categorize_sentiment(window)
        sentiments.append(sentiment)

    return sentiments


def load_and_analyze_ohlc_data(file_path, window_size=16):
    # Load the CSV file
    df = pd.read_csv(file_path, parse_dates=['timestamp'])

    # Ensure the data is sorted by timestamp
    df = df.sort_values('timestamp')

    # Rename columns to match the expected format
    df = df.rename(columns={
        'open': 'Open',
        'high': 'High',
        'low': 'Low',
        'close': 'Close'
    })

    # Calculate sentiments
    sentiments = analyze_ohlc_sentiment(df, window_size)

    # Add sentiments to the DataFrame
    df['Sentiment'] = sentiments + [np.nan] * (len(df) - len(sentiments))

    return df

# Usage
file_path = 'data/latest_coinbase.csv'
# file_path = 'data/BTC_USD_OHLC_60_20230727_20240827.csv'
analyzed_data = load_and_analyze_ohlc_data(file_path)

# Print the results
pd.set_option('display.max_rows', None)  # To show all rows
print(analyzed_data[['timestamp', 'Open', 'Close', 'Sentiment']])

# Optionally, save the results to a new CSV file
analyzed_data.to_csv('analyzed_ohlc_data.csv', index=False)
