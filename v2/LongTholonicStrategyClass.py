import pandas as pd


class LongTholonicStrategy:
    def __init__(self, params):
        self.negotiation_threshold = params['negotiation_threshold']
        self.limitation_multiplier = params['limitation_multiplier']
        self.contribution_threshold = params['contribution_threshold']
        self.lookback_period = params['lookback_period']

    def calculate_indicators(self, ohlcv_data):
        indicators = pd.DataFrame(index=ohlcv_data.index)

        # Calculate price change
        indicators['price_change'] = (ohlcv_data['close'] - ohlcv_data['open']) / ohlcv_data['open'] * 100

        # Calculate average volume
        indicators['average_volume'] = ohlcv_data['volume'].rolling(window=self.lookback_period).mean()

        # Calculate volatility
        indicators['volatility'] = ohlcv_data['close'].rolling(window=self.lookback_period).std()

        # Calculate average volatility
        indicators['average_volatility'] = indicators['volatility'].rolling(window=self.lookback_period).mean()

        return indicators

    def generate_signals(self, ohlcv_data, indicators):
        signals = pd.DataFrame(index=ohlcv_data.index)

        signals['negotiation_condition'] = indicators['price_change'] >= self.negotiation_threshold
        signals['limitation_condition'] = ohlcv_data['volume'] >= indicators['average_volume'] * self.limitation_multiplier
        signals['contribution_condition'] = indicators['volatility'] <= indicators['average_volatility'] * self.contribution_threshold

        signals['buy_signal'] = (
            signals['negotiation_condition'] &
            signals['limitation_condition'] &
            signals['contribution_condition']
        )

        signals['sell_signal'] = (
            (indicators['volatility'] < indicators['average_volatility']) &
            (indicators['volatility'].shift(1) >= indicators['average_volatility'].shift(1))
        )

        return signals

    def run_strategy(self, ohlcv_data):
        indicators = self.calculate_indicators(ohlcv_data)
        signals = self.generate_signals(ohlcv_data, indicators)
        return pd.concat([indicators, signals], axis=1)

# Usage example
params = {
    'negotiation_threshold': 0.5,
    'limitation_multiplier': 1.5,
    'contribution_threshold': 1.2,
    'lookback_period': 20
}

strategy = LongTholonicStrategy(params)
results = strategy.run_strategy(ohlcv_data)