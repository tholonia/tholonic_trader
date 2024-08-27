# Trading Strategy Backtester and Live Trader

## Overview

This Python program implements a versatile trading strategy tool that can function as both a backtester and a live trader. It focuses on cryptocurrency trading, allowing users to test strategies against historical data or execute trades in real-time using live market data from Kraken.

## Features

- Custom trading strategy implementation (Tholonic Strategy)
- Dual mode operation:
  - Backtesting using historical price data
  - Live trading using real-time data from Kraken
- Support for multiple trading pairs
- Configurable parameters via command-line arguments
- Profit and loss tracking
- Performance visualization
  - Individual trade profits/losses
  - Cumulative profit over time compared to buy-and-hold strategy
  - Asset closing prices over the trading period
- Profitability summary including:
  - Total number of trades
  - Number of profitable and non-profitable trades
  - Profit ratio
  - Total profit and profit percentage
  - Buy-and-hold return comparison

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

You can run the program using command-line arguments to set various parameters:

```
python trading_strategy_tool.py [options]
```

### Options:

- `-h, --help`: Show help message and exit
- `-p PAIR, --pair=PAIR`: Trading pair (e.g., BTCUSD)
- `-b, --backtest`: Run in backtest mode (default is live mode)
- `-m MAX, --max-positions=MAX`: Maximum number of positions
- `-n THRESHOLD, --negotiation=THRESHOLD`: Negotiation threshold
- `-l MULTIPLIER, --limitation=MULTIPLIER`: Limitation multiplier
- `-c THRESHOLD, --contribution=THRESHOLD`: Contribution threshold
- `-k PERIOD, --lookback=PERIOD`: Lookback period
- `-r RATE, --commission=RATE`: Commission rate
- `-s PERCENTAGE, --stop-loss=PERCENTAGE`: Stop loss percentage
- `-i BALANCE, --initial-balance=BALANCE`: Initial balance for buy-and-hold comparison

### Examples:

1. Run in backtest mode for BTCUSD with default settings:
   ```
   python trading_strategy_tool.py -b -p BTCUSD
   ```

2. Run live trading for ETHUSD with custom settings:
   ```
   python trading_strategy_tool.py -p ETHUSD -m 3 -n 1.2 -l 1.8 -c 1.5 -k 30 -r 0.002 -s 0.03
   ```

3. Run backtest with all parameters specified:
   ```
   python trading_strategy_tool.py -b -p BTCUSD -m 2 -n 1.0 -l 1.5 -c 1.2 -k 20 -r 0.001 -s 0.05 -i 1000
   ```

## Data Handling

- In backtest mode, the program reads historical data from CSV files in the `data/` directory. The file should be named according to the trading pair, e.g., `BTCUSD_OHLC_1440.csv`.
- In live mode, it fetches real-time data from Kraken using the CCXT library.

## Visualization

The program generates a plot with three subplots:

1. Individual trade profits/losses: A bar chart showing the profit or loss for each trade.
2. Cumulative profit vs Buy and Hold: A line chart comparing the strategy's cumulative profit to a buy-and-hold approach.
3. Asset Closing Prices: A line chart showing the closing prices of the asset over the trading period.

This visualization helps in understanding the strategy's performance in the context of market movements.

## Customization

You can customize the trading strategy by modifying the `TholonicStrategy` class in the source code. The main components to focus on are:

- `calculate_indicators()`: Define the indicators used by your strategy.
- `generate_signals()`: Implement the logic for generating buy and sell signals.

## Disclaimer

This program is for educational and research purposes only. It is not intended to be used as financial advice or a recommendation for any investment strategy. Always do your own research and consider seeking advice from a licensed financial advisor before making any investment decisions. When using the live trading mode, be aware of the risks involved in trading cryptocurrencies.

## Contributing

Contributions to improve the trading strategy tool are welcome. Please feel free to submit a Pull Request.

## License

This project is open-source and available under the MIT License.