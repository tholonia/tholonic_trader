#!/usr/bin/env python
"""
TensorBit: Bitcoin Price Prediction using LSTM

This script implements a deep learning model using LSTM (Long Short-Term Memory)
neural networks to predict Bitcoin prices based on historical OHLCV (Open, High, Low, Close, Volume) data.

Key Features:
1. Data Preprocessing: Reads and prepares Bitcoin price data from a CSV file.
2. Sliding Window Creation: Generates sliding windows of data for sequence-based learning.
3. Data Splitting: Separates data into training and validation sets.
4. Data Normalization: Scales the input features using StandardScaler.
5. Model Architecture: Implements a stacked LSTM model with dense layers.
6. Model Training: Compiles and trains the model on historical data.

Usage:
Ensure that the required libraries (numpy, pandas, tensorflow, sklearn) are installed.
Place your Bitcoin price data CSV file in the 'data' directory.
Run the script to train the model on your data.

Note: This script is designed for educational and experimental purposes.
It should not be used for actual financial decision-making without proper validation and risk assessment.


"""

import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# Read the CSV file
df = pd.read_csv('data/BTC_USD_OHLC_60_20230727_20240827.csv')  # Replace with your CSV file name

# Ensure the data is sorted by timestamp
df = df.sort_values('timestamp')

# Function to create sliding windows
def create_sliding_windows(data, window_size=16):
    windows = []
    for i in range(len(data) - window_size + 1):
        window = data[i:(i + window_size)]
        windows.append(window.values)
    return np.array(windows)

# Create sliding windows
window_size = 16
windowed_data = create_sliding_windows(df[['open', 'close', 'high', 'low', 'volume']], window_size)

# Split the data into features (X) and target (y)
X = windowed_data[:, :-1, :]  # All windows, all but the last entry, all 5 values
y = windowed_data[:, -1, :]   # All windows, only the last entry, all 5 values

# Split into training and validation sets
X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

# Normalize the data
scaler = StandardScaler()
X_train_shaped = X_train.reshape(-1, X_train.shape[-1])
X_val_shaped = X_val.reshape(-1, X_val.shape[-1])

X_train_scaled = scaler.fit_transform(X_train_shaped).reshape(X_train.shape)
X_val_scaled = scaler.transform(X_val_shaped).reshape(X_val.shape)

# Define the model
model = keras.Sequential([
    keras.layers.LSTM(64, input_shape=(15, 5), return_sequences=True),
    keras.layers.LSTM(32),
    keras.layers.Dense(16, activation='relu'),
    keras.layers.Dense(5)
])

# Compile the model
model.compile(optimizer='adam', loss='mse')

# Train the model
history = model.fit(X_train_scaled, y_train, epochs=50, batch_size=32,
                    validation_data=(X_val_scaled, y_val))

# Function to preprocess new data
def preprocess_new_data(new_data):
    new_data_shaped = new_data.reshape(-1, new_data.shape[-1])
    return scaler.transform(new_data_shaped).reshape(new_data.shape)

# Make predictions (example)
# Assuming you have the last 15 data points in a numpy array called 'last_15_points'
last_15_points = df[['open', 'close', 'high', 'low', 'volume']].values[-15:]

new_data = np.expand_dims(last_15_points, axis=0)  # Add batch dimension
new_data_scaled = preprocess_new_data(new_data)
prediction = model.predict(new_data_scaled)

print("Predicted next values (open, close, high, low, volume):", prediction[0])