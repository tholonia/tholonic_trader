import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import ccxt
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.widgets import MultiCursor
from colorama import Fore as fg, Back as bg

class DataLoader:
    def __init__(self, ohlcfile, from_date, to_date, livemode_n_elements=None):
        self.data = pd.read_csv(ohlcfile)
        self.data['timestamp'] = pd.to_datetime(self.data['timestamp'])
        self.data.set_index('timestamp', inplace=True)
        self.data = self.data.loc[from_date:to_date]
        if livemode_n_elements is not None:
            self.data = self.data.head(livemode_n_elements)
        self.last_record = self.data.iloc[-1] if not self.data.empty else None

    def get_data(self):
        return self.data

    def get_last_record(self):
        return self.last_record

class TholonicStrategy:
    def __init__(self, trading_pair, negotiation_threshold, limitation_multiplier,
                 contribution_threshold, lookback_period, livemode, livemode_n_elements,
                 ohlcfile, from_date, to_date):
        self.trading_pair = trading_pair
        self.lookback = lookback_period
        self.negotiation_threshold = negotiation_threshold
        self.limitation_multiplier = limitation_multiplier
        self.contribution_threshold = contribution_threshold
        self.livemode = livemode
        self.livemode_n_elements = livemode_n_elements

        if not self.livemode:
            loader = DataLoader(ohlcfile, from_date, to_date, self.livemode_n_elements)
            self.data = loader.get_data()
        else:
            self.data = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
            self.data.index.name = 'timestamp'
            self.exchange = ccxt.kraken({
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future'
                }
            })

    def fetch_ohlcv(self, symbol, timeframe, limit):
        ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df

    def update_data(self):
        if self.livemode:
            new_data = self.fetch_ohlcv(self.trading_pair, '1m', limit=self.lookback)
            if self.data.empty:
                self.data = new_data
            else:
                self.data = pd.concat([self.data, new_data]).drop_duplicates().sort_index().tail(self.lookback)

    def calculate_indicators(self):
        self.data['price_change'] = (self.data['close'] - self.data['open']) / self.data['open'] * 100
        self.data['average_volume'] = self.data['volume'].rolling(window=self.lookback).mean()
        self.data['volatility'] = self.data['close'].rolling(window=self.lookback).std()
        self.data['average_volatility'] = self.data['volatility'].rolling(window=self.lookback).mean()

    def generate_signals(self):
        self.data['negotiation_condition'] = self.data['price_change'] >= self.negotiation_threshold
        self.data['limitation_condition'] = self.data['volume'] >= self.data['average_volume'] * self.limitation_multiplier
        self.data['contribution_condition'] = self.data['volatility'] <= self.data['average_volatility'] * self.contribution_threshold
        self.data['buy_condition'] = (
            self.data['negotiation_condition'] &
            self.data['limitation_condition'] &
            self.data['contribution_condition']
        )
        self.data['sell_condition'] = (
            (self.data['volatility'] < self.data['average_volatility']) &
            (self.data['volatility'].shift(1) >= self.data['average_volatility'].shift(1))
        )

    def run_strategy(self):
        self.update_data()
        if self.data['volume'].iloc[-1] * self.data['close'].iloc[-1] < 5000:
            print(f"{self.trading_pair:10s}:Volume is too low: {int(self.data['volume'].iloc[-1]):8d} * {self.data['close'].iloc[-1]:8.2f} = {int(self.data['volume'].iloc[-1] * self.data['close'].iloc[-1]):8d}")
            exit()
        self.calculate_indicators()
        self.generate_signals()
        return self.data.iloc[-1]

    def get_signal(self):
        latest_data = self.data.iloc[-1]
        if latest_data['buy_condition']:
            return 'BUY'
        elif latest_data['sell_condition']:
            return 'SELL'
        else:
            return 'HOLD'

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

def print_trading_info(
        idx,
        timestamp,
        trading_pair,
        signal,
        close_price,
        avg_position_price,
        total_profit,
        total_profit_percentage,
        long_positions,
        num_positions,
        order_submission_status,
        value_in_assets_held,
        transaction_profit = None,
    ):

    base_message = f"{trading_pair}{idx:04d} Timestamp: {timestamp}, Pair: {trading_pair}, Signal: {signal}, Close Price: {close_price:.2f}, Total Units Held: {value_in_assets_held:.6f}, Avg Position: {avg_position_price:.2f}, Total Profit: {total_profit:.2f} ({total_profit_percentage:.2f}%), Long Positions: {long_positions}, Num Positions: {num_positions}"

    if signal == "HOLD":
        pass
        # print(fg.BLUE + base_message + fg.RESET)

    elif signal == "BUY":
        _ts = f"{timestamp}"
        _tp = f"{trading_pair}"
        _cp = f"Close: ${close_price:.2f}"
        _th = f"Total Units Held: {value_in_assets_held:.6f}"
        _ap = f"Avg Pos: ${avg_position_price}"
        _np = f"Num Pos: {num_positions}"

        base_message = f"{idx:04d} {_ts} {signal:5s}, {_tp}, {_cp}, {_th}, {_ap}, {_np}"

        if order_submission_status != "unavailable":
            print(fg.RED + base_message + fg.RESET)
        else:
            print(fg.LIGHTBLUE_EX + base_message + " unavailable" + fg.RESET)

    elif signal == "SELL":

        _ts = f"{timestamp}"
        _tp = f"{trading_pair}"
        _cp = f"Close: ${close_price:.2f}"
        _tP = f"Total Profit: {fg.MAGENTA}{total_profit:.2f}{fg.GREEN}"
        _tPp = f"{fg.MAGENTA}{total_profit_percentage:.2f}%"
        if transaction_profit <0:
            _tPt = f"{bg.RED}{fg.BLACK}{transaction_profit:.2f}%{bg.RESET}{fg.RESET}"
        else:
            _tPt = f"{fg.GREEN}{transaction_profit:.2f}%{fg.RESET}"

        base_message = f"{idx:04d} {_ts} {signal:5s}, {_tp}, {_cp}, {_tP}, {_tPp}, {_tPt}"
        print(fg.GREEN + base_message + fg.RESET+"\n")

    else:
        print(fg.WHITE + base_message + fg.RESET)



def calculate_average_position_price(positions):
    if not positions:
        return 0
    total_cost = sum(price * amount for price, amount in positions)
    total_amount = sum(amount for _, amount in positions)
    return total_cost / total_amount if total_amount > 0 else 0

def calculate_profit(entry_positions, exit_price, exit_amount, commission_rate):
    avg_entry_price = calculate_average_position_price(entry_positions)
    gross_profit = (exit_price - avg_entry_price) * exit_amount
    entry_commission = avg_entry_price * exit_amount * commission_rate
    exit_commission = exit_price * exit_amount * commission_rate
    net_profit = gross_profit - entry_commission - exit_commission
    total_investment = avg_entry_price * exit_amount
    net_profit_percentage = (net_profit / total_investment) * 100 if total_investment > 0 else 0
    return net_profit, net_profit_percentage

def check_stop_loss(positions, current_price, stop_loss_percentage):
    if not positions:
        return False
    avg_entry_price = calculate_average_position_price(positions)
    stop_loss_price = avg_entry_price * (1 - stop_loss_percentage)
    return current_price <= stop_loss_price

FCY = fg.CYAN
FLB = fg.LIGHTBLUE_EX
FLM = fg.LIGHTMAGENTA_EX
FLG = fg.LIGHTGREEN_EX
FLY = fg.LIGHTYELLOW_EX
FLC = fg.LIGHTCYAN_EX
FRE = fg.RED
FYE = fg.YELLOW
FXX = fg.RESET