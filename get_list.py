#!/bin/env python

import requests

import requests

def get_and_print_kraken_wsnames():
    url = "https://api.kraken.com/0/public/AssetPairs"

    try:
        response = requests.get(url)
        response.raise_for_status()

        data = response.json()

        if data['error']:
            print(f"Error from Kraken API: {data['error']}")
            return

        print("WebSocket Names:")
        for pair_data in data['result'].values():
            wsname = pair_data.get('wsname', 'Not available')
            print(wsname)

    except requests.RequestException as e:
        print(f"An error occurred while fetching data: {e}")

if __name__ == "__main__":
    get_and_print_kraken_wsnames()