#!/bin/env python
import pandas as pd
import argparse
from datetime import datetime

def merge_excel_files(file1, index1, file2, index2, output_file):
    # Read the Excel files with specified index columns
    df1 = pd.read_excel(file1, index_col=index1, parse_dates=True)
    df2 = pd.read_excel(file2, index_col=index2, parse_dates=True)

    # Ensure the index is named 'Timestamp' for clarity
    df1.index.name = 'Timestamp'
    df2.index.name = 'Timestamp'

    # Merge the dataframes
    merged_df = pd.merge(df1, df2, left_index=True, right_index=True, how='outer')

    # Sort the merged dataframe by timestamp
    merged_df.sort_index(inplace=True)

    # Write the merged dataframe to a new Excel file
    merged_df.to_excel(output_file)
    print(f"Merged data written to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge two Excel files based on specified timestamp index columns.")
    parser.add_argument("file1", help="Path to the first Excel file")
    parser.add_argument("index1", help="Index column for the first file (e.g., 'A' or 0 for first column)")
    parser.add_argument("file2", help="Path to the second Excel file")
    parser.add_argument("index2", help="Index column for the second file (e.g., 'B' or 1 for second column)")
    parser.add_argument("output", help="Path for the output Excel file")
    args = parser.parse_args()

    # Convert column letters to column numbers if necessary
    def column_to_index(col):
        if col.isalpha():
            return ord(col.upper()) - ord('A')
        return int(col)

    index1 = column_to_index(args.index1)
    index2 = column_to_index(args.index2)

    merge_excel_files(args.file1, index1, args.file2, index2, args.output)