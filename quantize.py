#!/bin/env python3
"""
quantize.py: Price Data Quantization and Signature Generation

This script provides functionality for quantizing price data and generating
unique signatures based on the quantized data. It also includes database
operations for storing and retrieving these signatures.

Key Features:
1. Price data normalization and quantization
2. Generation of unique signatures for price patterns
3. SQLite database integration for storing signatures

Dependencies:
- pandas: For data manipulation and analysis
- numpy: For numerical operations
- sqlite3: For database operations
- os: For file and directory operations
- datetime: For timestamp handling

Main Functions:
- create_price_set_signature: Generates a unique signature for a given price dataset
- create_database: Sets up the SQLite database for storing signatures

Usage:
This script can be imported as a module in other Python scripts or
run standalone to process price data and generate signatures.

Note: Ensure all dependencies are installed before running this script.
"""

import pandas as pd
import numpy as np
import sqlite3
import os
from datetime import datetime

def create_price_set_signature(price_data, num_bands=20):
    if not isinstance(price_data, pd.Series):
        price_data = pd.Series(price_data)

    price_data = price_data.dropna()

    if len(price_data) < num_bands:
        raise ValueError(f"Not enough data points. Expected at least {num_bands}, got {len(price_data)}")

    band_size = len(price_data) // num_bands

    # Handle case where all prices are the same
    if price_data.std() == 0:
        normalized_prices = pd.Series([0] * len(price_data))
    else:
        normalized_prices = (price_data - price_data.mean()) / price_data.std()

    bands = [normalized_prices[i:i+band_size] for i in range(0, len(normalized_prices), band_size)]
    bands = bands[:num_bands] + [pd.Series()] * (num_bands - len(bands))

    signature_components = []
    for band in bands:
        if len(band) > 0:
            avg = band.mean()
            trend = np.polyfit(range(len(band)), band, 1)[0] if len(band) > 1 else 0
            volatility = band.std()
        else:
            avg, trend, volatility = 0, 0, 0

        # Handle NaN values
        avg = 0 if np.isnan(avg) else avg
        trend = 0 if np.isnan(trend) else trend
        volatility = 0 if np.isnan(volatility) else volatility

        avg_quantized = int((avg + 3) * 10)
        trend_quantized = int((trend + 1) * 50)
        volatility_quantized = int(volatility * 50)

        band_signature = avg_quantized * 10000 + trend_quantized * 100 + volatility_quantized
        signature_components.append(str(band_signature).zfill(6))

    return "-".join(signature_components)

def create_database(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS signatures
    (signature TEXT PRIMARY KEY)
    ''')

    conn.commit()
    conn.close()
    print(f"Database '{db_path}' has been created.")

def process_ohlc_file(file_path, db_path, window_size=20):
    if not os.path.exists(db_path):
        create_database(db_path)
    else:
        print(f"Using existing database: '{db_path}'")

    df = pd.read_csv(file_path, parse_dates=['timestamp'])
    df.set_index('timestamp', inplace=True)
    df.sort_index(inplace=True)

    unique_signatures = set()

    for i in range(0, len(df) - window_size + 1):
        window = df.iloc[i:i+window_size]
        close_prices = window['close']
        try:
            signature = create_price_set_signature(close_prices)
            unique_signatures.add(signature)
        except ValueError as e:
            print(f"Skipping window {i} due to error: {e}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    for sig in unique_signatures:
        cursor.execute('INSERT OR IGNORE INTO signatures (signature) VALUES (?)', (sig,))

    conn.commit()
    conn.close()

    return len(unique_signatures)


def print_all_signatures(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM signatures ORDER BY signature ASC")
    all_signatures = cursor.fetchall()

    print(f"{'Signature'}")
    print("-" * 80)

    for sig in all_signatures:
        print(f"{sig[0]}")

    print(f"\nTotal unique signatures: {len(all_signatures)}")

    conn.close()

def clear_database(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM signatures")
        conn.commit()
        print("All records have been deleted from the database.")
        print(f"Number of records deleted: {cursor.rowcount}")
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        conn.rollback()
    finally:
        conn.close()

def drop_database(db_path):
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"Database '{db_path}' has been successfully dropped.")
        else:
            print(f"Database '{db_path}' does not exist.")
    except Exception as e:
        print(f"An error occurred while trying to drop the database: {e}")


if __name__ == "__main__":
    import sys

    file_path = 'data/BTC_USD_OHLC_60_20230727_20240827.csv'  # Replace with your actual file path
    db_path = 'ohlc_signatures.db'

    if len(sys.argv) > 1:
        if sys.argv[1] == "--clear":
            clear_database(db_path)
        elif sys.argv[1] == "--drop":
            drop_database(db_path)
            sys.exit(0)
        else:
            print("Invalid argument. Use --clear to clear the database or --drop to delete it entirely.")
            sys.exit(1)

    # Process with basic parameters
    window_size = 20

    print(f"Processing OHLC file: {file_path}")
    print(f"Using database: {db_path}")

    unique_count = process_ohlc_file(file_path, db_path, window_size)
    print(f"Total unique signatures saved to database: {unique_count}")

    print("\nAll Unique Signatures in the Database:")
    print_all_signatures(db_path)

    # Debug: Print some sample signatures
    df = pd.read_csv(file_path, parse_dates=['timestamp'])
    df.set_index('timestamp', inplace=True)
    df.sort_index(inplace=True)

    print("\nSample Signatures:")
    for i in range(5):
        window = df.iloc[i:i+window_size]
        close_prices = window['close']
        try:
            signature = create_price_set_signature(close_prices)
            print(f"Window {i}: {signature}")
        except ValueError as e:
            print(f"Window {i}: Error - {e}")

    df = pd.read_csv(file_path, parse_dates=['timestamp'])
    df.set_index('timestamp', inplace=True)
    df.sort_index(inplace=True)

    unique_signatures = set()

    for i in range(0, len(df) - window_size + 1):
        window = df.iloc[i:i+window_size]
        close_prices = window['close']
        try:
            signature = create_price_set_signature(close_prices)
            unique_signatures.add(signature)
        except ValueError as e:
            print(f"Skipping window {i} due to error: {e}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS signatures
    (signature TEXT PRIMARY KEY)
    ''')

    for sig in unique_signatures:
        cursor.execute('INSERT OR IGNORE INTO signatures (signature) VALUES (?)', (sig,))

    conn.commit()
    conn.close()



# if __name__ == "__main__":
#     import sys

#     file_path = 'BTC_USD_OHLC_60_20230727_20240827.csv'
#     db_path = 'ohlc_signatures.db'

#     if len(sys.argv) > 1:
#         if sys.argv[1] == "--clear":
#             clear_database(db_path)
#         elif sys.argv[1] == "--drop":
#             drop_database(db_path)
#             sys.exit(0)
#         else:
#             print("Invalid argument. Use --clear to clear the database or --drop to delete it entirely.")
#             sys.exit(1)

#     # Process with basic parameters
#     window_size = 20

#     unique_count = process_ohlc_file(file_path, db_path, window_size)
#     print(f"Total unique signatures saved to database: {unique_count}")

#     print("\nAll Unique Signatures in the Database:")
#     print_all_signatures(db_path)

#     # Debug: Print some sample signatures
#     df = pd.read_csv(file_path, parse_dates=['timestamp'])
#     df.set_index('timestamp', inplace=True)
#     df.sort_index(inplace=True)

#     print("\nSample Signatures:")
#     for i in range(5):
#         window = df.iloc[i:i+window_size]
#         close_prices = window['close']
#         try:
#             signature = create_price_set_signature(close_prices)
#             print(f"Window {i}: {signature}")
#         except ValueError as e:
#             print(f"Window {i}: Error - {e}")