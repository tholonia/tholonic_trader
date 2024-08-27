# Trading Strategy Backtester and Live Trader

## Overview

This Python program implements a versatile trading strategy tool that can function as both a backtester and a live trader. It focuses on cryptocurrency trading, allowing users to test strategies against historical data or execute trades in real-time using live market data from Kraken.

## Features

- Custom trading strategy implementation (Tholonic Strategy)
- Dual mode operation:
  - Backtesting using historical price data
  - Live trading using real-time data from Kraken
- Support for multiple trading pairs
- Configurable parameters including:
  - Maximum number of positions
  - Negotiation threshold
  - Limitation multiplier
  - Contribution threshold
  - Lookback period
  - Commission rate
  - Stop loss percentage
- Profit and loss tracking
- Performance visualization
  - Individual trade profits/losses
  - Cumulative profit over time
  - Comparison with buy-and-hold strategy (in backtest mode)
- Profitability summary including:
  - Total number of trades
  - Number of profitable and non-profitable trades
  - Profit ratio
  - Total profit and profit percentage
  - Buy-and-hold return comparison (in backtest mode)

## Requirements

- Python 3.7+
- pandas
- numpy
- ccxt
- colorama
- matplotlib

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/trading-strategy-tool.git
   cd trading-strategy-tool
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Backtesting Mode

1. Ensure you have historical price data in CSV format in the `data/` directory. The file should be named according to the trading pair, e.g., `BTCUSD_OHLC_1440.csv`.

2. Set `backtest = True` in the main script.

3. Modify the parameters in the `if __name__ == "__main__":` section of the script to adjust the strategy settings.

4. Run the script:
   ```
   python trading_strategy_tool.py
   ```

### Live Trading Mode

1. Set `backtest = False` in the main script.

2. Ensure you have set up your Kraken API credentials (refer to the Kraken API documentation for details on how to obtain and set up API keys).

3. Modify the parameters in the `if __name__ == "__main__":` section of the script to adjust the strategy settings.

4. Run the script:
   ```
   python trading_strategy_tool.py
   ```

In live mode, the program will fetch real-time data from Kraken and execute the strategy based on current market conditions.

## Configuration

Key parameters to configure:

```python
backtest = True  # Set to False for live trading
trading_pair = "BTCUSD"
max_positions = 2
negotiation_threshold = 1.0
limitation_multiplier = 1.5
contribution_threshold = 1.2
lookback_period = 20
commission_rate = 0.001
stop_loss_percentage = 0.05
initial_balance = 1000  # Used for buy-and-hold comparison in backtest mode
```

## Customization

You can customize the trading strategy by modifying the `TholonicStrategy` class. The main components to focus on are:

- `calculate_indicators()`: Define the indicators used by your strategy.
- `generate_signals()`: Implement the logic for generating buy and sell signals.

## Data Handling

- In backtest mode, the program reads historical data from CSV files.
- In live mode, it fetches real-time data from Kraken using the CCXT library.

## Disclaimer

This program is for educational and research purposes only. It is not intended to be used as financial advice or a recommendation for any investment strategy. Always do your own research and consider seeking advice from a licensed financial advisor before making any investment decisions. When using the live trading mode, be aware of the risks involved in trading cryptocurrencies.

## Contributing

Contributions to improve the trading strategy tool are welcome. Please feel free to submit a Pull Request.

## License

This project is open-source and available under the MIT License.