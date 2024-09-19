import ccxt
from decimal import Decimal
from typing import List, Optional
import json

class CoinbaseTransactionManager:
    """
    A class to manage transactions on Coinbase Pro using the CCXT library.
    """

    def __init__(self, sandbox=True):
        """
        Initialize the CoinbaseTransactionManager.

        :param api_key: Your Coinbase Pro API key
        :param api_secret: Your Coinbase Pro API secret
        :param passphrase: Your Coinbase Pro API passphrase
        :param sandbox: Boolean to enable sandbox mode for testing (default: False)
        """

        credentials_file = ".coinbase"

        with open(credentials_file, "r") as f:
            credentials = json.load(f)

        self.exchange = ccxt.coinbase({
            'apiKey': credentials['apiKey'],
            'secret': credentials['privateKey'],
            'password': credentials['password'],
            'enableRateLimit': True,
            'sandboxMode': sandbox,
        })

        self.offline = True

    def _create_order(self, symbol, order_type, side, amount, price=None, params={}):
        """
        Internal method to create an order.

        :param symbol: Trading pair symbol (e.g., 'BTC/USD')
        :param order_type: Type of order (e.g., 'market', 'limit', 'stop')
        :param side: 'buy' or 'sell'
        :param amount: Amount of the asset to trade
        :param price: Price for limit orders (optional)
        :param params: Additional parameters for the order (optional)
        :return: Order details if successful, None otherwise
        """
        if self.offline:
            print(f"Offline: Would have created {order_type} {side} order for {amount} {symbol}")
            return None
        try:
            return self.exchange.create_order(symbol, order_type, side, amount, price, params)
        except Exception as e:
            print(f"Error creating {order_type} {side} order: {str(e)}")
            return None

    def buy_market_order(self, symbol, amount):
        """
        Place a market buy order.

        Use this when you want to buy immediately at the best available price.

        :param symbol: Trading pair symbol (e.g., 'BTC/USD')
        :param amount: Amount of the asset to buy
        :return: Order details if successful, None otherwise
        """
        if self.offline:
            print(f"Offline: Would have created market buy order for {amount} {symbol}")
            return None
        return self._create_order(symbol, 'market', 'buy', amount)

    def sell_market_order(self, symbol, amount):
        """
        Place a market sell order.

        Use this when you want to sell immediately at the best available price.

        :param symbol: Trading pair symbol (e.g., 'BTC/USD')
        :param amount: Amount of the asset to sell
        :return: Order details if successful, None otherwise
        """
        if self.offline:
            print(f"Offline: Would have created market sell order for {amount} {symbol}")
            return None
        return self._create_order(symbol, 'market', 'sell', amount)

    def buy_limit_order(self, symbol, amount, price):
        """
        Place a limit buy order.

        Use this when you want to buy at a specific price or better.

        :param symbol: Trading pair symbol (e.g., 'BTC/USD')
        :param amount: Amount of the asset to buy
        :param price: Maximum price you're willing to pay
        :return: Order details if successful, None otherwise
        """
        if self.offline:
            print(f"Offline: Would have created limit buy order for {amount} {symbol} at {price}")
            return None
        return self._create_order(symbol, 'limit', 'buy', amount, price)

    def sell_limit_order(self, symbol, amount, price):
        """
        Place a limit sell order.

        Use this when you want to sell at a specific price or better.

        :param symbol: Trading pair symbol (e.g., 'BTC/USD')
        :param amount: Amount of the asset to sell
        :param price: Minimum price you're willing to accept
        :return: Order details if successful, None otherwise
        """
        if self.offline:
            print(f"Offline: Would have created limit sell order for {amount} {symbol} at {price}")
            return None
        return self._create_order(symbol, 'limit', 'sell', amount, price)

    def buy_stop_order(self, symbol, amount, stop_price):
        """
        Place a stop buy order.

        Use this when you want to buy when the price reaches a certain level.
        This is often used to enter a position or limit losses.

        :param symbol: Trading pair symbol (e.g., 'BTC/USD')
        :param amount: Amount of the asset to buy
        :param stop_price: Price at which the stop order becomes active
        :return: Order details if successful, None otherwise
        """
        if self.offline:
            print(f"Offline: Would have created stop buy order for {amount} {symbol} at {stop_price}")
            return None
        params = {'stopPrice': stop_price}
        return self._create_order(symbol, 'stop', 'buy', amount, None, params)

    def sell_stop_order(self, symbol, amount, stop_price):
        """
        Place a stop sell order.

        Use this when you want to sell when the price reaches a certain level.
        This is often used to limit losses or protect profits.

        :param symbol: Trading pair symbol (e.g., 'BTC/USD')
        :param amount: Amount of the asset to sell
        :param stop_price: Price at which the stop order becomes active
        :return: Order details if successful, None otherwise
        """
        if self.offline:
            print(f"Offline: Would have created stop sell order for {amount} {symbol} at {stop_price}")
            return None
        params = {'stopPrice': stop_price}
        return self._create_order(symbol, 'stop', 'sell', amount, None, params)

    def buy_stop_limit_order(self, symbol, amount, price, stop_price):
        """
        Place a stop-limit buy order.

        Use this when you want to buy at a specific price after the market reaches a certain stop price.
        This combines the features of stop and limit orders.

        :param symbol: Trading pair symbol (e.g., 'BTC/USD')
        :param amount: Amount of the asset to buy
        :param price: Limit price for the order
        :param stop_price: Price at which the stop-limit order becomes active
        :return: Order details if successful, None otherwise
        """
        if self.offline:
            print(f"Offline: Would have created stop-limit buy order for {amount} {symbol} at {price} with stop price {stop_price}")
            return None
        params = {'stopPrice': stop_price}
        return self._create_order(symbol, 'stop_limit', 'buy', amount, price, params)

    def sell_stop_limit_order(self, symbol, amount, price, stop_price):
        """
        Place a stop-limit sell order.

        Use this when you want to sell at a specific price after the market reaches a certain stop price.
        This combines the features of stop and limit orders.

        :param symbol: Trading pair symbol (e.g., 'BTC/USD')
        :param amount: Amount of the asset to sell
        :param price: Limit price for the order
        :param stop_price: Price at which the stop-limit order becomes active
        :return: Order details if successful, None otherwise
        """
        if self.offline:
            print(f"Offline: Would have created stop-limit sell order for {amount} {symbol} at {price} with stop price {stop_price}")
            return None
        params = {'stopPrice': stop_price}
        return self._create_order(symbol, 'stop_limit', 'sell', amount, price, params)

    def buy_trailing_stop_order(self, symbol, amount, trail_amount):
        """
        Place a trailing stop buy order.

        Use this when you want to buy when the price drops by a certain amount or percentage from a peak.
        This is useful for entering positions in a rising market.

        :param symbol: Trading pair symbol (e.g., 'BTC/USD')
        :param amount: Amount of the asset to buy
        :param trail_amount: The trailing amount (absolute or percentage)
        :return: Order details if successful, None otherwise
        """
        if self.offline:
            print(f"Offline: Would have created trailing stop buy order for {amount} {symbol} with trail amount {trail_amount}")
            return None
        params = {'trailAmount': trail_amount}
        return self._create_order(symbol, 'trailing_stop', 'buy', amount, None, params)

    def sell_trailing_stop_order(self, symbol, amount, trail_amount):
        """
        Place a trailing stop sell order.

        Use this when you want to sell when the price rises by a certain amount or percentage from a low.
        This is useful for protecting profits in a falling market.

        :param symbol: Trading pair symbol (e.g., 'BTC/USD')
        :param amount: Amount of the asset to sell
        :param trail_amount: The trailing amount (absolute or percentage)
        :return: Order details if successful, None otherwise
        """
        if self.offline:
            print(f"Offline: Would have created trailing stop sell order for {amount} {symbol} with trail amount {trail_amount}")
            return None
        params = {'trailAmount': trail_amount}
        return self._create_order(symbol, 'trailing_stop', 'sell', amount, None, params)

    def buy_take_profit_order(self, symbol, amount, take_profit_price):
        """
        Place a take-profit buy order.

        Use this when you want to buy when the price reaches a certain level, typically to close a short position.

        :param symbol: Trading pair symbol (e.g., 'BTC/USD')
        :param amount: Amount of the asset to buy
        :param take_profit_price: Price at which the take-profit order is triggered
        :return: Order details if successful, None otherwise
        """
        if self.offline:
            print(f"Offline: Would have created take-profit buy order for {amount} {symbol} at {take_profit_price}")
            return None
        params = {'takeProfitPrice': take_profit_price}
        return self._create_order(symbol, 'take_profit', 'buy', amount, None, params)

    def sell_take_profit_order(self, symbol, amount, take_profit_price):
        """
        Place a take-profit sell order.

        Use this when you want to sell when the price reaches a certain level, typically to realize profits.

        :param symbol: Trading pair symbol (e.g., 'BTC/USD')
        :param amount: Amount of the asset to sell
        :param take_profit_price: Price at which the take-profit order is triggered
        :return: Order details if successful, None otherwise
        """
        if self.offline:
            print(f"Offline: Would have created take-profit sell order for {amount} {symbol} at {take_profit_price}")
            return None
        params = {'takeProfitPrice': take_profit_price}
        return self._create_order(symbol, 'take_profit', 'sell', amount, None, params)

    def get_order_status(self, order_id):
        """
        Fetch the status of an order.

        Use this to check the current state of an order (e.g., 'open', 'closed', 'canceled').

        :param order_id: The ID of the order to check
        :return: Order status details if successful, None otherwise
        """
        if self.offline:
            print(f"Offline: Would have fetched order status for {order_id}")
            return None
        try:
            return self.exchange.fetch_order(order_id)
        except Exception as e:
            print(f"Error fetching order status: {str(e)}")
            return None

    def get_order_ids(self, symbol: Optional[str] = None, since: Optional[int] = None, limit: Optional[int] = None) -> List[str]:
        """
        Fetch order IDs from Coinbase Pro.

        :param symbol: Trading symbol (e.g., 'BTC/USD'). If None, fetches orders for all symbols.
        :param since: Timestamp in milliseconds for the earliest order to fetch
        :param limit: Maximum number of orders to fetch
        :return: List of order IDs
        """
        try:
            orders = self.exchange.fetch_orders(symbol=symbol, since=since, limit=limit)
            return [order['id'] for order in orders]
        except ccxt.NetworkError as e:
            print(f"Network error: {str(e)}")
            return []
        except ccxt.ExchangeError as e:
            print(f"Exchange error: {str(e)}")
            return []
        except Exception as e:
            print(f"An unexpected error occurred: {str(e)}")
            return []


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


