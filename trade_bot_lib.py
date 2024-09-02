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
        self.macd = None
        self.signal = None
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

    # def determine_movement(self):

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

    def calculate_macd(self, fast_period=12, slow_period=26, signal_period=9):
        # Calculate the MACD
        exp1 = self.data['close'].ewm(span=fast_period, adjust=False).mean()
        exp2 = self.data['close'].ewm(span=slow_period, adjust=False).mean()
        self.macd = exp1 - exp2
        self.signal = self.macd.ewm(span=signal_period, adjust=False).mean()

        # Determine if it's bullish or bearish based on the MACD line's direction
        if len(self.macd) >= 2:
            if (
                self.macd.iloc[-1] > self.macd.iloc[-4] and
                self.macd.iloc[-4] > self.macd.iloc[-8]
            ):
                return "BULL"   #! ?? if I return -1,1,0 instead, it finds no transactions !?
            elif (
                self.macd.iloc[-1] < self.macd.iloc[-4] and
                self.macd.iloc[-4] < self.macd.iloc[-8]
            ):
                return "BEAR"
            elif abs(self.data['close'].iloc[-1] - self.data['close'].iloc[-2]) < 0.0001:
                return "FLAT"
            else:
                return "UNKNOWN"
        else:
            # Not enough data to determine direction
            return "FLAT"

    def run_strategy(self):
        self.update_data()
        if self.data['volume'].iloc[-1] * self.data['close'].iloc[-1] < 5000:
            print(f"{self.trading_pair:10s}:Volume is too low: {int(self.data['volume'].iloc[-1]):8d} * {self.data['close'].iloc[-1]:8.2f} = {int(self.data['volume'].iloc[-1] * self.data['close'].iloc[-1]):8d}")
            exit()
        self.calculate_indicators()
        self.generate_signals()

        # Calculate MACD signal
        macd_signal = self.calculate_macd()

        # Add MACD signal and values to the latest data
        latest_data = self.data.iloc[-1].copy()
        latest_data['macd_signal'] = macd_signal
        latest_data['macd'] = self.macd.iloc[-1] if self.macd is not None else None
        latest_data['macd_signal_line'] = self.signal.iloc[-1] if self.signal is not None else None

        return latest_data

    def get_signal(self):
        latest_data = self.data.iloc[-1]
        macd_signal = self.calculate_macd()

        if latest_data['buy_condition']:# and macd_signal == "BEAR" or macd_signal == "FLAT":
            return 'BUY'
        elif latest_data['sell_condition']:# or macd_signal == "BULL":
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

def generate_report(trading_pair, negotiation_threshold, limitation_multiplier, contribution_threshold,
                    lookback_period, stop_loss_percentage, from_date, to_date, total_trades,
                    profitable_trades, non_profitable_trades, first_purchase_price, final_selling_price,
                    total_profit, total_profit_percentage, current_capital, last_value_in_assets_held,
                    hodl_percentage, avg_vol_price, verbosity_level, ohlcfile, write_cvs_header_once):

    FCY = fg.CYAN
    FLB = fg.LIGHTBLUE_EX
    FLM = fg.LIGHTMAGENTA_EX
    FLG = fg.LIGHTGREEN_EX
    FLY = fg.LIGHTYELLOW_EX
    FLC = fg.LIGHTCYAN_EX
    FRE = fg.RED
    FYE = fg.YELLOW
    FXX = fg.RESET

    profit_ratio = profitable_trades / total_trades if total_trades > 0 else 0

    CX = f"{trading_pair}"
    NT = f"{negotiation_threshold}"
    LT = f"{limitation_multiplier}"
    CT = f"{contribution_threshold}"
    KP = f"{lookback_period}"
    SL = f"{stop_loss_percentage}"
    PS = f"{CX} n:{NT} l:{LT} c:{CT} k:{KP} s:{SL}{fg.RESET}"
    FR = f"{from_date}"
    TO = f"{to_date}"
    TT = f"{total_trades}"
    PT = f"{profitable_trades}"
    PN = f"{non_profitable_trades}"
    PR = f"{profit_ratio:.2%}"
    IC = f"${first_purchase_price:.2f}"
    FS = f"${final_selling_price:.2f}"
    TP = f"${total_profit:.2f})"
    TC = f"{total_profit_percentage:.2f}%"
    HP = f"{hodl_percentage:.2f}%"
    FC = f"${current_capital:.2f}"
    TR = f"{(current_capital - first_purchase_price) / first_purchase_price * 100:.2f}%"
    TH = f"{last_value_in_assets_held:.6f}"
    HC = f"{total_profit_percentage - hodl_percentage:.2f}%"
    AV = f"${avg_vol_price:.2f}"

    ch = {
        'CX': "trading_pair",
        'NT': "negotiation_threshold",
        'LT': "limitation_multiplier",
        'CT': "contribution_threshold",
        'KP': "lookback_period",
        'SL': "stop_loss_percentage",
        'FR': "from_date",
        'TO': "to_date",
        'TT': "total_trades",
        'PT': "profitable_trades",
        'PN': "non_profitable_trades",
        'PR': "profit_ratio",
        'IC': "first_purchase_price",
        'FS': "final_selling_price",
        'TP': "total_profit",
        'TC': "total_profit_percentage",
        'TR': "total_return",
        'BH': "buy_and_hold_return",
        'FC': "current_capital",
        'TH': "last_value_in_assets_held",
        'HP': "HOLD_percentage",
        'HC': "HODL_compare",
        'AV': "avg_vol_price",
    }

    if verbosity_level > 0 and verbosity_level < 100:
        str = f"""
        {fg.CYAN}
        PS: Profitability Summary:         {PS}
        FR: {ch['FR']:30s} {FR}
        TO: {ch['TO']:30s} {TO}
        TT: {ch['TT']:30s} {TT}
        PT: {ch['PT']:30s} {PT}
        PN: {ch['PN']:30s} {PN}
        PR: {ch['PR']:30s} {PR}

        IC: {ch['IC']:30s} {IC}
        FS: {ch['FS']:30s} {FS}
        TP: {ch['TP']:30s} {TP}
        BH: {ch['BH']:30s} {HP}

        FC: {ch['FC']:30s} {FC}
        TR: {ch['TR']:30s} {TR}
        TH: {ch['TH']:30s} {TH}
        HP: {ch['HP']:30s} {HP}
        HC: {ch['HC']:30s} {HC}
        AV: {ch['AV']:30s} {AV}
        {fg.RESET}

        """
        print(str)

    if verbosity_level == 101:
        str  = f"{FCY}{CX:10s}{FXX}"
        str += f"{FLB}n:{NT:.1f}{FXX}"
        str += F"{FLC}l:{LT:.1f}{FXX}"
        str += f"{FLM}c:{CT:.1f}{FXX}"
        str += f"{FLG}k:{KP:02d}{FXX}"
        str += f"{FLB}s:{SL:>.1f}{FXX}"
        str += f"|{FR} - {TO}"
        str += f"|TT: {FCY}{TT:4d}{FXX}"
        str += f"|PN: {FYE}{PT:3d}/{PN:3d}{FXX}"
        str += f"|HC: {FLY}{HC:+6.2f}%{FXX}"
        str += f"|TH: {FLG}{TH:8.6f}{FXX}"
        str += f"|AV: {FLC}${AV:>12,.2f}{FXX}"
        print(str)

        cvsheader  = f"{ohlcfile},{ch['NT']},{ch['LT']},{ch['CT']},{ch['KP']},{ch['SL']},{ch['FR']},{ch['TO']},"
        cvsheader += f"{ch['TT']},{ch['PT']},{ch['PN']},{ch['PR']},{ch['IC']},{ch['FS']},{ch['TP']},{ch['TC']},"
        cvsheader += f"{ch['BH']},{ch['FC']},{ch['TH']},{ch['AV']},{ch['HP']},{ch['HC']}"

        csvstr  = f"{ohlcfile},{NT},{LT},{CT},{KP},{SL},{FR},{TO},"
        csvstr += f"{TT},{PT},{PN},{PR},{IC},{FS},{TP},{TC},"
        csvstr += f"{HP},{FC},{TH},{AV},{HP},{HC}"

        if write_cvs_header_once:
            print(cvsheader,file=open("results.csv","w"),flush=True)
            return False
        else:
            print(csvstr,file=open("results.csv","a"),flush=True)
            return write_cvs_header_once


FCY = fg.CYAN
FLB = fg.LIGHTBLUE_EX
FLM = fg.LIGHTMAGENTA_EX
FLG = fg.LIGHTGREEN_EX
FLY = fg.LIGHTYELLOW_EX
FLC = fg.LIGHTCYAN_EX
FRE = fg.RED
FYE = fg.YELLOW
FXX = fg.RESET