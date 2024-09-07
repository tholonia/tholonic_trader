"""
DataLoader Class

This class is responsible for loading and managing OHLCV (Open, High, Low, Close, Volume) data
for financial analysis and trading strategies.

Key Features:
1. Loads data from a CSV file
2. Supports date range filtering
3. Implements a sliding window mechanism for data analysis
4. Provides methods to access and manipulate the loaded data

Attributes:
    data (pandas.DataFrame): The current window of OHLCV data
    full_data (pandas.DataFrame): The complete dataset loaded from the CSV file
    livemode_n_elements (int): Number of elements in each data window
    current_window_start (int): Starting index of the current data window
    last_record (pandas.Series): The last record in the current data window

Methods:
    __init__(self, ohlcfile, from_date, to_date, livemode_n_elements):
        Initializes the DataLoader with the specified parameters
    update_data_window(self):
        Updates the current data window based on the window start and size
    shift_window(self, n=1):
        Shifts the data window by a specified number of steps
    get_data(self):
        Returns the current data window

Usage:
    Initialize the class with the CSV file path, date range, and window size.
    Use shift_window() to move through the dataset and get_data() to retrieve the current window.

Note: This class is designed for use in financial analysis and algorithmic trading applications.
Ensure that the input CSV file is properly formatted with the required OHLCV columns.
"""


import pandas as pd
from colorama import Fore as fg, Back as bg
import trade_bot_vars as v


# class DataLoader:
#     def __init__(self, ohlcfile, from_date, to_date, livemode_n_elements=None):
#         self.data = pd.read_csv(ohlcfile)
#         self.data['timestamp'] = pd.to_datetime(self.data['timestamp'])
#         self.data.set_index('timestamp', inplace=True)
#         self.data = self.data.loc[from_date:to_date]
#         if livemode_n_elements is not None:
#             self.data = self.data.head(livemode_n_elements)
#         self.last_record = self.data.iloc[-1] if not self.data.empty else None

#     def get_data(self):
#         return self.data

#     def get_last_record(self):
#         return self.last_record


class DataLoader:
    def __init__(self, ohlcfile, from_date, to_date, livemode_n_elements):
        self.data = pd.read_csv(ohlcfile)
        self.data['timestamp'] = pd.to_datetime(self.data['timestamp'])
        self.data.set_index('timestamp', inplace=True)
        self.full_data = self.data.loc[from_date:to_date]
        self.livemode_n_elements = livemode_n_elements
        self.current_window_start = 0
        self.update_data_window()

    def update_data_window(self):
        if self.livemode_n_elements is not None:
            end_index = self.current_window_start + self.livemode_n_elements
            self.data = self.full_data.iloc[self.current_window_start:end_index]
        else:
            self.data = self.full_data

        self.last_record = self.data.iloc[-1] if not self.data.empty else None

    def shift_window(self, n=1):
        if self.livemode_n_elements is not None:
            self.current_window_start += self.livemode_n_elements * n
            self.current_window_start = min(self.current_window_start, len(self.full_data) - self.livemode_n_elements)
            self.current_window_start = max(self.current_window_start, 0)
            self.update_data_window()

    def get_data(self):
        return self.data

    def get_last_record(self):
        return self.last_record