"""
ProfitLossPlotterClass.py: Profit/Loss Visualization for Trading Bot

This module contains the ProfitLossPlotter class, which is responsible for
visualizing the performance of the trading bot. It tracks and plots various
metrics including profits, prices, trade points, and volatility.

Key Features:
1. Tracking of trades, profits, and prices over time
2. Visualization of cumulative profits and individual trade points
3. Calculation and plotting of price deltas and moving averages
4. Volatility tracking and visualization
5. Comprehensive multi-panel plot generation for performance analysis

Main Class:
- ProfitLossPlotter: Handles data storage and plotting functionality

Dependencies:
- pandas: For data manipulation
- matplotlib: For creating plots
- colorama: For colored console output

Usage:
Instantiate the ProfitLossPlotter class and use its methods to add trade data
and generate plots. This class is typically used in conjunction with the main
trading bot script to provide visual insights into the bot's performance.

Note: Ensure all dependencies are installed before using this class.
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.widgets import MultiCursor
from colorama import Fore as fg, Back as bg



class ProfitLossPlotter:
    def __init__(self):
        self.timestamps = []
        self.profits = []
        self.cumulative_profits = []
        self.prices = []
        self.buy_points = []
        self.sell_points = []
        self.price_deltas = []
        self.sma_price_deltas = []
        self.volatilities = []
        self.average_volatilities = []

    def add_trade(self, timestamp, profit, price, trade_type=None, volatility=None, average_volatility=None, available_positions=0):
        self.timestamps.append(timestamp)
        self.profits.append(profit)
        self.prices.append(price)
        if not self.cumulative_profits:
            self.cumulative_profits.append(profit)
        else:
            self.cumulative_profits.append(self.cumulative_profits[-1] + profit)
        if trade_type == 'BUY' and available_positions > 0:
            self.buy_points.append((timestamp, price))
        elif trade_type == 'SELL' and available_positions > 0:
            self.sell_points.append((timestamp, price))
        if len(self.prices) > 1:
            price_delta = (price - self.prices[-2]) / self.prices[-2] * 100
            self.price_deltas.append(price_delta)
        else:
            self.price_deltas.append(0)
        if len(self.price_deltas) >= 14:
            sma = sum(self.price_deltas[-14:]) / 14
            self.sma_price_deltas.append(sma)
        else:
            self.sma_price_deltas.append(0)
        self.volatilities.append(volatility)
        self.average_volatilities.append(average_volatility)

    def plot(self, initial_balance, negotiation_threshold, limitation_multiplier,
             contribution_threshold, lookback_period, volatility, verbosity,
             stop_loss, ohlcfile, total_profit_percentage, buy_and_hold_return):
        fig, axes = plt.subplots(3, 1, figsize=(23, 13), sharex=True)
        ax1, ax2, ax4 = axes
        dates = pd.to_datetime(self.timestamps)
        plt.rcParams.update({'font.size': 8})

        ax1.bar(dates, self.profits, color=['g' if p > 0 else 'r' for p in self.profits])
        ax1.set_title('.')
        ax1.set_ylabel('Profit/Loss')
        ax1.axhline(y=0, color='k', linestyle='-', linewidth=0.5)

        ax2.plot(dates, self.cumulative_profits, color='b', label='Strategy', zorder=3)
        initial_price = self.prices[0]
        buy_and_hold_values = [initial_balance * (price / initial_price) - initial_balance for price in self.prices]
        ax2.plot(dates, buy_and_hold_values, color='r', label='Buy and Hold', zorder=3)
        ax2.set_title('Cumulative Profit vs Buy and Hold')
        ax2.set_ylabel('Profit')
        ax2.legend()

        date_to_index = {date: index for index, date in enumerate(dates)}
        buy_dates = [pd.to_datetime(date) for date, _ in self.buy_points]
        buy_indices = [date_to_index.get(date) for date in buy_dates if date in date_to_index]
        buy_values = [buy_and_hold_values[i] for i in buy_indices if i is not None]
        ax2.scatter(buy_dates, buy_values, color='darkviolet', marker='v', s=30, label='Buy', zorder=2)

        sell_dates = [pd.to_datetime(date) for date, _ in self.sell_points]
        sell_indices = [date_to_index.get(date) for date in sell_dates if date in date_to_index]
        sell_values = [buy_and_hold_values[i] for i in sell_indices if i is not None]
        ax2.scatter(sell_dates, sell_values, color='lime', marker='^', s=30, label='Sell', zorder=2)

        ax2.legend(['Strategy', 'Buy and Hold', 'Buy', 'Sell'])

        ax4.plot(dates, self.volatilities, color='b', label='Volatility (STD)')
        ax4.plot(dates, self.average_volatilities, color='r', label='Average Volatility')
        ax4.set_title('Volatility (STD) and Average Volatility')
        ax4.set_ylabel('Volatility')
        ax4.legend()

        plt.gcf().autofmt_xdate()
        plt.subplots_adjust(left=0.1, right=0.95, bottom=0.1, top=0.95)

        title = f"n{negotiation_threshold}l{limitation_multiplier}c{contribution_threshold}k{lookback_period}s{stop_loss}"
        title += f" [{ohlcfile}]"
        title += f" hold:{buy_and_hold_return:.2f}% net:{total_profit_percentage:.2f}% Δ{total_profit_percentage-buy_and_hold_return:.2f}%"
        plt.suptitle(title, fontsize=16)

        for ax in axes:
            ax.xaxis.set_major_locator(mdates.MonthLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_minor_locator(mdates.DayLocator())
            ax.tick_params(axis='x', which='major', rotation=45, labelsize=8, pad=15)
            ax.tick_params(axis='x', which='minor', length=4, width=0.5, labelsize=0)
            ax.tick_params(axis='y', labelsize=8)
            ax.grid(which='minor', axis='x', linestyle=':', linewidth=0.5, alpha=0.7)
            ax.grid(which='major', axis='x', linestyle='-', linewidth=0.8, alpha=0.9)

        plt.tight_layout()
        multi = MultiCursor(fig.canvas, (ax1, ax2, ax4), color='r', lw=1, horizOn=True, vertOn=True)

        p = ohlcfile.replace("data/", "").split("_")
        pairname = f"{p[0]}_{p[1]}"
        plot_name = f"{pairname}_n{negotiation_threshold}l{limitation_multiplier}c{contribution_threshold}k{lookback_period}s{stop_loss:.3f}_{total_profit_percentage-buy_and_hold_return:04.2f}.png"
        plt.savefig("img/" + plot_name, dpi=100, bbox_inches='tight')
        if verbosity != 101:
            plt.show()
        plt.close()
