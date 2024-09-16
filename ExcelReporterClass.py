"""
ExcelReporterClass.py: Excel Report Generation for Trading Bot

This module contains the ExcelReporter class, which is responsible for
creating and managing Excel reports for the trading bot's performance.

Key Features:
1. Creation and loading of Excel workbooks
2. Writing headers and appending data rows
3. Applying color coding to rows based on trading signals
4. Automatic column width adjustment for better readability

Main Class:
- ExcelReporter: Handles Excel file operations and report formatting

Dependencies:
- openpyxl: For Excel file manipulation
- os: For file system operations

Usage:
Instantiate the ExcelReporter class and use its methods to create
and populate Excel reports with trading data. This class is typically
used in conjunction with the main trading bot script to generate
performance reports.

Example:
    reporter = ExcelReporter("trading_report.xlsx")
    reporter.write_header(["Date", "Price", "Signal"])
    reporter.append_row(["2023-01-01", 50000, "BUY"])
    reporter.apply_row_color(2, "BUY")
    reporter.adjust_column_width()
    reporter.save()

Note: Ensure openpyxl is installed before using this class.
"""

import os
from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

class ExcelReporter:
    def __init__(self, file_name="line_results.xlsx"):
        self.file_name = file_name
        self.wb = None
        self.ws = None
        self.load_or_create_workbook()


    def set_column_format(self, column, number_format):
        """
        Set the number format for an entire column.

        :param column: Column letter (e.g., 'A', 'B') or number (1, 2, ...)
        :param number_format: Number format code (e.g., '0.00%', '$#,##0.00')
        """
        if isinstance(column, int):
            column = get_column_letter(column)

        for cell in self.ws[column]:
            cell.number_format = number_format
    def load_or_create_workbook(self):
        if os.path.exists(self.file_name):
            self.wb = load_workbook(self.file_name)
            self.ws = self.wb.active
        else:
            self.wb = Workbook()
            self.ws = self.wb.active

    def write_header(self, headers):
        if self.ws.max_row == 1:  # Only write header if sheet is empty
            self.ws.append(headers)

    def append_row(self, row_data):
        self.ws.append(row_data)
        return self.ws.max_row

    def apply_row_color(self, row_number, signal):
        red_fill = PatternFill(start_color="FFf5b7b1", end_color="FFf5b7b1", fill_type="solid")
        green_fill = PatternFill(start_color="FFd5f5e3", end_color="FFd5f5e3", fill_type="solid")

        fill = red_fill if signal == "BUY" else green_fill if signal == "SELL" else None

        if fill:
            for cell in self.ws[row_number]:
                cell.fill = fill

    def adjust_column_width(self):
        for column in self.ws.columns:
            max_length = 0
            column_letter = get_column_letter(column[0].column)
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(cell.value)
                except:
                    pass
            adjusted_width = (max_length + 2) * 1.2
            self.ws.column_dimensions[column_letter].width = adjusted_width

    def add_table(self):
        table_name = "TradingData"
        table_ref = f"A1:{get_column_letter(self.ws.max_column)}{self.ws.max_row}"

        # Check if the table already exists
        if table_name not in self.ws.tables:
            tab = Table(displayName=table_name, ref=table_ref)
            style = TableStyleInfo(name="TableStyleMedium9", showFirstColumn=False,
                                   showLastColumn=False, showRowStripes=True, showColumnStripes=True)
            tab.tableStyleInfo = style
            self.ws.add_table(tab)
        else:
            # Update existing table range
            self.ws.tables[table_name].ref = table_ref

    def save(self):
        self.wb.save(self.file_name)

    def update_report(self, data, headers):
        self.write_header(headers)
        row_number = self.append_row(data)
        self.apply_row_color(row_number, data[2])  # Assuming 'signal' is the 3rd item in data
        self.adjust_column_width()
        self.add_table()
        self.save()