#!/usr/bin/env python
"""
CSVtoSQL.py: Convert CSV to SQLite Database

This script converts a CSV file to an SQLite database. It reads a CSV file specified as a command-line argument,
processes the data, and creates an SQLite database with the same name as the CSV file (but with a .db extension).

Usage:
    python CSVtoSQL.py <csv_file_name>

Arguments:
    csv_file_name: The name of the CSV file to be converted.

Features:
    - Deletes existing database file if it exists
    - Reads CSV file using pandas
    - Drops 'Time Test Option' column if present
    - Renames columns to be Python-friendly (lowercase, spaces replaced with underscores)
    - Creates SQLite database and table based on CSV structure
    - Inserts CSV data into the SQLite database
    - Handles various exceptions and provides informative error messages
    - Logs operations and errors

Dependencies:
    - pandas
    - sqlalchemy
    - logging

Note:
    Ensure you have the necessary permissions to read the CSV file and write to the directory
    where the script is located.

Author: [Your Name]
Date: [Current Date]
Version: 1.0
"""

import pandas as pd
import os
import sys
from sqlalchemy import create_engine, Column, Float, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Check if CSV file name is provided as command-line argument
if len(sys.argv) < 2:
    logging.error("Please provide the CSV file name as a command-line argument.")
    logging.error("Usage: python script_name.py your_csv_file.csv")
    sys.exit(1)

# Get CSV file name from command-line argument
csv_file = sys.argv[1]

# Create database file name based on CSV file name
db_file = os.path.splitext(csv_file)[0] + '.db'

# Check if the database file exists and delete it
if os.path.exists(db_file):
    os.remove(db_file)
    logging.info(f"Existing database '{db_file}' has been deleted.")

# Read the CSV file
try:
    df = pd.read_csv(csv_file)
    logging.info(f"Successfully read CSV file '{csv_file}'. Shape: {df.shape}")
except FileNotFoundError:
    logging.error(f"Error: The file '{csv_file}' was not found.")
    sys.exit(1)
except pd.errors.EmptyDataError:
    logging.error(f"Error: The file '{csv_file}' is empty.")
    sys.exit(1)
except Exception as e:
    logging.error(f"An error occurred while reading the file: {str(e)}")
    sys.exit(1)

# Drop the 'Time Test Option' column if it exists
if 'Time Test Option' in df.columns:
    df = df.drop('Time Test Option', axis=1)

# Rename columns to remove spaces and make them Python-friendly
df.columns = df.columns.str.replace(' ', '_').str.lower()

# Create a SQLite database
engine = create_engine(f'sqlite:///{db_file}', echo=False)

# Create a base class for declarative class definitions
Base = declarative_base()

# Define the table structure dynamically based on CSV columns
class TradeData(Base):
    __tablename__ = 'trade_data'
    id = Column(Integer, primary_key=True)

    # Dynamically add columns based on CSV structure
    for column in df.columns:
        if column.lower() in ['fromdate', 'todate']:
            locals()[column.lower()] = Column(String)  # Changed to String for flexibility
        elif df[column].dtype == 'float64':
            locals()[column.lower()] = Column(Float)
        elif df[column].dtype == 'int64':
            locals()[column.lower()] = Column(Integer)
        else:
            locals()[column.lower()] = Column(String)

# Create the table
Base.metadata.create_all(engine)
logging.info("Database table created successfully.")

# Create a session
Session = sessionmaker(bind=engine)
session = Session()

# Convert DataFrame to list of dictionaries
data = df.to_dict('records')

# Insert data into the database
try:
    for i, record in enumerate(data):
        trade_data = TradeData(**record)
        session.add(trade_data)
        if (i + 1) % 1000 == 0:  # Log progress every 1000 records
            logging.info(f"Inserted {i + 1} records...")

    session.commit()
    logging.info(f"All {len(data)} records inserted successfully.")
except SQLAlchemyError as e:
    session.rollback()
    logging.error(f"An error occurred while inserting data: {str(e)}")
    sys.exit(1)
finally:
    session.close()

# Verify data insertion
verify_engine = create_engine(f'sqlite:///{db_file}', echo=False)
verify_session = sessionmaker(bind=verify_engine)()
count = verify_session.query(TradeData).count()
verify_session.close()

if count == len(data):
    logging.info(f"Data verification successful. {count} records found in the database.")
else:
    logging.warning(f"Data verification failed. Expected {len(data)} records, but found {count} in the database.")

print(f"Data from '{csv_file}' has been processed. Check the logs for details.")