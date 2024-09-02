#!/bin/env python

#!/usr/bin/env python
import sys
import getopt
import requests
import pandas as pd
from datetime import datetime, timedelta

BASE_URL = 'https://api.pro.coinbase.com'

def get_coinbase_product_id(crypto, base):
    """
    Construct the Coinbase product ID based on the crypto and base symbols.
    :param crypto: Cryptocurrency symbol (e.g., 'BTC', 'ETH')
    :param base: Base currency symbol (e.g., 'USD', 'EUR')
    :return: Coinbase product ID
    """
    return f"{crypto}-{base}"

def fetch_ohlc_data(product_id, start, end, granularity=3600):
    """
    Fetch OHLC (Open, High, Low, Close) data from Coinbase API.
    :param product_id: The trading pair (e.g., 'BTC-USD')
    :param start: Start time in ISO 8601 format
    :param end: End time in ISO 8601 format
    :param granularity: Time frame interval in seconds (3600 for 1-hour)
    :return: List of OHLC data
    """
    url = f"{BASE_URL}/products/{product_id}/candles"
    params = {
        'start': start,
        'end': end,
        'granularity': granularity
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        print(f"Error fetching data: {response.status_code} - {response.text}")
        return None
    return response.json()

def ohlc_to_dataframe(ohlc_data):
    """
    Convert OHLC data to a pandas DataFrame.
    :param ohlc_data: List of OHLC data
    :return: DataFrame with columns: ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    """
    df = pd.DataFrame(ohlc_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
    df = df.sort_values('timestamp')
    return df

def save_to_csv(df, filename):
    """
    Save DataFrame to a CSV file.
    :param df: DataFrame to save
    :param filename: The file name for the CSV file
    """
    df['timestamp'] = df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    df.to_csv(filename, index=False)
    print(f"Data saved to {filename}")

def parse_date(date_str):
    """
    Parse date string to ISO 8601 format.
    :param date_str: Date string in format YYYY-MM-DD
    :return: ISO 8601 formatted string
    """
    return datetime.strptime(date_str, "%Y-%m-%d").isoformat()

def main(argv):
    crypto_symbol = ''
    base_symbol = ''
    from_date = ''
    to_date = ''
    granularity = 3600  # Default to 1 hour

    try:
        opts, args = getopt.getopt(argv, "hc:b:f:t:g:", ["crypto=", "base=", "from=", "to=", "granularity="])
    except getopt.GetoptError:
        print('script.py -c <crypto_symbol> -b <base_symbol> -f <from_date> -t <to_date> -g <granularity>')
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print('script.py -c <crypto_symbol> -b <base_symbol> -f <from_date> -t <to_date> -g <granularity>')
            sys.exit()
        elif opt in ("-c", "--crypto"):
            crypto_symbol = arg.upper()
        elif opt in ("-b", "--base"):
            base_symbol = arg.upper()
        elif opt in ("-f", "--from"):
            from_date = arg
        elif opt in ("-t", "--to"):
            to_date = arg
        elif opt in ("-g", "--granularity"):
            granularity = int(arg)

    if not all([crypto_symbol, base_symbol, from_date, to_date]):
        print("All arguments are required.")
        sys.exit(2)

    product_id = get_coinbase_product_id(crypto_symbol, base_symbol)
    start = parse_date(from_date)
    end = parse_date(to_date)

    print(f"Fetching data for {product_id} from {from_date} to {to_date} with granularity {granularity} seconds...")

    all_data = []
    current_start = start
    while current_start < end:
        current_end = min(datetime.fromisoformat(current_start) + timedelta(days=300), datetime.fromisoformat(end))
        ohlc_data = fetch_ohlc_data(product_id, current_start, current_end.isoformat(), granularity)
        if ohlc_data:
            all_data.extend(ohlc_data)
        else:
            print(f"No data fetched for period {current_start} to {current_end}.")
        current_start = current_end.isoformat()

    if all_data:
        df = ohlc_to_dataframe(all_data)
        df = df[(df['timestamp'] >= pd.Timestamp(from_date)) & (df['timestamp'] <= pd.Timestamp(to_date))]
        filename = f"data/{crypto_symbol}_{base_symbol}_OHLC_{granularity}_{from_date.replace('-', '')}_{to_date.replace('-', '')}.csv"
        save_to_csv(df, filename)
    else:
        print("No data fetched for the entire period.")

if __name__ == '__main__':
    main(sys.argv[1:])