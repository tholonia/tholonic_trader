#!/bin/bash

# # Define the range for K
# start_k=4
# end_k=32  # You can adjust this to your desired end value

# # Loop through the range
# for K in $(seq $start_k $end_k)
# do
#     ./trade_bot.py -v 101 -n 0.4 -l -0.2 -c 1.2 -k 15 -F data/BTCUSD_OHLC_60.csv -s 1 -m 1 -R "2024-07-27|now"
# done


# best for 1hr n0.5, l0.3, c1.3 k15


# Define the range for K
start_k=0
end_k=6 # You can adjust this to your desired end value
increment=0.2

# Function to compare floating point numbers
float_cmp() {
    awk -v n1="$1" -v n2="$2" 'BEGIN {if (n1<=n2) exit 0; exit 1}'
}

# Loop through the range
K=$start_k
while float_cmp $K $end_k
do
    ./trade_bot.py -v 101 -n 0.0 -l 0.4 -c 1 -k 14 -s 3.6  -F data/BTC_USD_OHLC_30_20230815_20240826.csv -m 1 -R "2023-08-15|2024-08-26"

    # Increment K
    K=$(awk -v k=$K -v inc=$increment 'BEGIN {print k+inc}')
done