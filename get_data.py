#!/usr/bin/env python
import sys
import getopt
import requests
import pandas as pd
from datetime import datetime

def get_kraken_asset_pairs():
    """
    Fetch all asset pair information from Kraken API.
    :return: Dictionary of asset pairs and their details
    """
    url = 'https://api.kraken.com/0/public/AssetPairs'
    response = requests.get(url)
    data = response.json()

    if data['error']:
        print("Error fetching asset pair information:", data['error'])
        return None

    return data['result']

def create_comprehensive_mapping(asset_pairs):
    """
    Create comprehensive mappings between altnames, common names, and Kraken internal codes.
    :param asset_pairs: Dictionary of asset pairs from Kraken API
    :return: Three dictionaries for different mapping purposes
    """
    altname_to_pair = {}
    common_to_pair = {}
    pair_to_altname = {}

    for pair, details in asset_pairs.items():
        altname = details['altname']
        wsname = details.get('wsname')
        base = details['base']
        quote = details['quote']

        altname_to_pair[altname] = pair
        pair_to_altname[pair] = altname

        if wsname:
            common_pair = wsname.replace('/', '')
            common_to_pair[common_pair] = pair

        # Handle special cases like XBT/BTC
        if base == 'XXBT':
            common_to_pair[f"BTC{quote[1:]}"] = pair
        if quote == 'XXBT':
            common_to_pair[f"{base[1:]}BTC"] = pair

    return altname_to_pair, common_to_pair, pair_to_altname

def get_kraken_pair_name(crypto, base, common_to_pair, altname_to_pair):
    """
    Construct the correct Kraken pair name based on the crypto and base symbols.
    :param crypto: Cryptocurrency symbol (e.g., 'BTC', 'ETH')
    :param base: Base currency symbol (e.g., 'USD', 'EUR')
    :param common_to_pair: Dictionary mapping common names to Kraken pair names
    :param altname_to_pair: Dictionary mapping altnames to Kraken pair names
    :return: Kraken pair name
    """
    common_name = f"{crypto}{base}"
    if common_name in common_to_pair:
        return common_to_pair[common_name]
    if common_name in altname_to_pair:
        return altname_to_pair[common_name]
    raise ValueError(f"Could not find a valid Kraken pair for {crypto}/{base}")

def fetch_ohlc_data(pair='XXBTZUSD', interval=1440, since=None):
    """
    Fetch OHLC (Open, High, Low, Close) data from Kraken API.
    :param pair: The trading pair (e.g., 'XXBTZUSD' for BTC/USD)
    :param interval: Time frame interval in minutes (1440 for 1-day)
    :param since: Timestamp to start fetching data (in Unix time)
    :return: List of OHLC data
    """
    url = 'https://api.kraken.com/0/public/OHLC'
    params = {
        'pair': pair,
        'interval': interval,
        'since': since
    }
    response = requests.get(url, params=params)
    data = response.json()
    if data['error']:
        print("Error fetching data:", data['error'])
        return None
    return data['result'][pair]

def ohlc_to_dataframe(ohlc_data):
    """
    Convert OHLC data to a pandas DataFrame.
    :param ohlc_data: List of OHLC data
    :return: DataFrame with columns: ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    """
    df = pd.DataFrame(ohlc_data, columns=['Time', 'Open', 'High', 'Low', 'Close', 'vwap', 'Volume', 'Count'])
    df['Time'] = pd.to_datetime(df['Time'], unit='s')
    df[['Open', 'High', 'Low', 'Close', 'Volume']] = df[['Open', 'High', 'Low', 'Close', 'Volume']].apply(pd.to_numeric)
    df = df.rename(columns={
        'Time': 'timestamp',
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'close',
        'Volume': 'volume'
    })
    return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

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
    Parse date string to Unix timestamp.
    :param date_str: Date string in format YYYY-MM-DD
    :return: Unix timestamp
    """
    return int(datetime.strptime(date_str, "%Y-%m-%d").timestamp())

def main(argv):
    crypto_symbol = ''
    base_symbol = ''
    from_date = ''
    to_date = ''
    interval = 1440  # Default to 1 day

    try:
        opts, args = getopt.getopt(argv, "hc:b:f:t:i:", ["crypto=", "base=", "from=", "to=", "interval="])
    except getopt.GetoptError:
        print('script.py -c <crypto_symbol> -b <base_symbol> -f <from_date> -t <to_date> -i <interval>')
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print('script.py -c <crypto_symbol> -b <base_symbol> -f <from_date> -t <to_date> -i <interval>')
            sys.exit()
        elif opt in ("-c", "--crypto"):
            crypto_symbol = arg.upper()
        elif opt in ("-b", "--base"):
            base_symbol = arg.upper()
        elif opt in ("-f", "--from"):
            from_date = arg
        elif opt in ("-t", "--to"):
            to_date = arg
        elif opt in ("-i", "--interval"):
            interval = int(arg)

    if not all([crypto_symbol, base_symbol, from_date, to_date]):
        print("All arguments are required.")
        sys.exit(2)

    asset_pairs = get_kraken_asset_pairs()
    if asset_pairs is None:
        print("Failed to fetch asset pair information. Exiting.")
        sys.exit(1)

    altname_to_pair, common_to_pair, pair_to_altname = create_comprehensive_mapping(asset_pairs)

    try:
        pair = get_kraken_pair_name(crypto_symbol, base_symbol, common_to_pair, altname_to_pair)
    except ValueError as e:
        print(str(e))
        sys.exit(1)

    since = parse_date(from_date)
    until = parse_date(to_date)

    print(f"Fetching data for {pair} (common name: {pair_to_altname[pair]}) from {from_date} to {to_date} with interval {interval}...")
    ohlc_data = fetch_ohlc_data(pair=pair, interval=interval, since=since)

    if ohlc_data:
        df = ohlc_to_dataframe(ohlc_data)
        df = df[(df['timestamp'] >= pd.Timestamp(from_date)) & (df['timestamp'] <= pd.Timestamp(to_date))]
        filename = f"data/{crypto_symbol}_{base_symbol}_OHLC_{interval}_{from_date.replace('-', '')}_{to_date.replace('-', '')}.csv"
        save_to_csv(df, filename)
    else:
        print("No data fetched.")

if __name__ == '__main__':
    main(sys.argv[1:])