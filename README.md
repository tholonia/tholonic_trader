# Cimulator: Cryptocurrency Trading Bot Simulator

Cimulator is a comprehensive cryptocurrency trading bot simulator designed to test and optimize trading strategies using historical or live market data. It provides a flexible framework for backtesting, data analysis, and strategy implementation.

## Features

- Support for multiple data sources (CSV files and live exchange data)
- Sentiment analysis for market conditions
- Customizable trading strategies
- Performance profiling and optimization tools
- Detailed reporting and visualization of trading results

## Components

1. **cimulator.py**: Main script for running simulations
2. **DataManagerClass.py**: Handles data loading and processing
3. **TholonicStrategyClass.py**: Implements trading strategies
4. **SentimentClass.py**: Performs sentiment analysis on market data
5. **ExcelReporterClass.py**: Generates Excel reports of trading results
6. **cimulator_lib.py**: Utility functions for the project
7. **GlobalsClass.py**: Manages global variables and state
8. **get_data_COINBASE.py**: Fetches data from Coinbase API
9. **CSVtoSQL.py**: Converts CSV data to SQLite database
10. **PROFILER**: Bash script for performance profiling
11. **NOWSENTIMENT**: Bash script for real-time sentiment analysis

## Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/cimulator.git
   cd cimulator
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up configuration:
   - Copy `cfg/cimulator.toml.example` to `cfg/cimulator.toml`
   - Edit `cfg/cimulator.toml` with your desired settings

## Usage

1. Run a simulation:
   ```
   python cimulator.py
   ```

2. Fetch latest Coinbase data:
   ```
   ./get_data_COINBASE.py
   ```

3. Perform real-time sentiment analysis:
   ```
   ./NOWSENTIMENT
   ```

4. Profile the application:
   ```
   ./PROFILER
   ```

5. Convert CSV to SQLite:
   ```
   python CSVtoSQL.py your_csv_file.csv
   ```

## Testing

Run the data management tests:
```
python test_datamanager.py
```

## Configuration

The main configuration file is `cfg/cimulator.toml`. Key settings include:

- Data source (CSV or live exchange)
- Trading pair
- Strategy parameters
- Date range for backtesting
- Reporting options

## Contributing

Contributions are welcome! Please read the contributing guidelines before submitting pull requests.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Disclaimer

This software is for educational purposes only. Do not use it for actual trading without understanding the risks involved in cryptocurrency trading.