#!/bin/env python
from CoinbaseClass import CoinbaseTransactionManager
import ccxt
from typing import List, Dict
import time
import json



# Usage example:
# api_key = 'your_api_key'
# api_secret = 'your_api_secret'
# passphrase = 'your_passphrase'
# manager = CoinbaseTransactionManager(api_key, api_secret, passphrase)
# order = manager.buy_market_order('BTC/USD', 0.01)
# if order:
#     print(f"Order placed: {order['id']}")
#     status = manager.get_order_status(order['id'])
#     print(f"Order status: {status['status']}")




cb = CoinbaseTransactionManager()

import time
symbol = "BTC/USD"
since = int(time.time() - 86400) * 1000  # Last 24 hours
limit = 100

order_ids =cb.get_order_ids(symbol, since, limit)
print(order_ids)

# if order_ids:
#     print(f"Fetched {len(order_ids)} order IDs:")
#     for order_id in order_ids:
#         print(order_id)
# else:
#     print("No orders found or an error occurred.")