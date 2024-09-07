#!/usr/bin/env python

"""
CSVtoSQL.py: Convert CSV file to SQLite database

This script reads a CSV file and converts it into a SQLite database. It's designed to work
with strategy results CSV files, typically containing trading strategy performance metrics.

Key features:
1. Accepts CSV file name as a command-line argument
2. Creates a SQLite database file with the same name as the input CSV file
3. Deletes existing database file if it exists
4. Reads the CSV file using pandas
5. Preprocesses the data by dropping the 'Time Test Option' column if present
6. Renames columns to be Python-friendly (removes spaces, converts to lowercase)
7. Creates a SQLite database and table based on the CSV structure
8. Inserts the CSV data into the SQLite database

Usage:
    python CSVtoSQL.py <csv_file_name>

Arguments:
    csv_file_name: Name of the CSV file to be converted

Output:
    A SQLite database file (.db) with the same name as the input CSV file

Dependencies:
    - pandas
    - sqlalchemy

Note: This script assumes a specific structure for the input CSV file, typically
containing trading strategy results. Modify the script if your CSV structure differs.
"""

import pandas as pd
import os
import sys
from sqlalchemy import create_engine, Column, Float, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Check if CSV file name is provided as command-line argument
if len(sys.argv) < 2:
    print("Please provide the CSV file name as a command-line argument.")
    print("Usage: python script_name.py your_csv_file.csv")
    sys.exit(1)

# Get CSV file name from command-line argument
csv_file = sys.argv[1]

# Create database file name based on CSV file name
db_file = os.path.splitext(csv_file)[0] + '.db'

# Check if the database file exists and delete it
if os.path.exists(db_file):
    os.remove(db_file)
    print(f"Existing database '{db_file}' has been deleted.")

# Read the CSV file
try:
    df = pd.read_csv(csv_file)
except FileNotFoundError:
    print(f"Error: The file '{csv_file}' was not found.")
    sys.exit(1)
except pd.errors.EmptyDataError:
    print(f"Error: The file '{csv_file}' is empty.")
    sys.exit(1)
except Exception as e:
    print(f"An error occurred while reading the file: {str(e)}")
    sys.exit(1)

# Drop the 'Time Test Option' column if it exists
if 'Time Test Option' in df.columns:
    df = df.drop('Time Test Option', axis=1)

# Rename columns to remove spaces and make them Python-friendly
df.columns = df.columns.str.replace(' ', '_').str.lower()

# Create a SQLite database
engine = create_engine(f'sqlite:///{db_file}', echo=True)

# Create a base class for declarative class definitions
Base = declarative_base()

# Define the table structure
class TradeData(Base):
    __tablename__ = 'trade_data'

    id = Column(Integer, primary_key=True)
    negotiation_threshold = Column(Float)
    limitation_multiplier = Column(Float)
    contribution_threshold = Column(Float)
    lookback_period = Column(Integer)
    total_return = Column(Float)
    number_of_trades = Column(Integer)
    win_rate = Column(Float)
    staroverhodl = Column(Float)
    entry_sentiment = Column(String)
    exit_sentiment = Column(String)

# Create the table
Base.metadata.create_all(engine)

# Create a session
Session = sessionmaker(bind=engine)
session = Session()

# Convert DataFrame to list of dictionaries
data = df.to_dict('records')

# Insert data into the database
for record in data:
    trade_data = TradeData(**record)
    session.add(trade_data)

# Commit the changes and close the session
session.commit()
session.close()

print(f"Data from '{csv_file}' has been successfully imported into the new SQL database '{db_file}'.")