#!/bin/bash

# use the default values, optimizsed for 1hr

#./get_data.py -c SOL -b USD -f 2024-07-27 -t 2024-08-27 -i 60
#./get_data.py -c XBT -b USD -f 2024-07-27 -t 2024-08-27 -i 60
#./get_data.py -c XDG -b USD -f 2024-07-27 -t 2024-08-27 -i 60
#./get_data.py -c ETH -b USD -f 2024-07-27 -t 2024-08-27 -i 60

FT="2024-07-27|2024-08-27"
V="-v 101"
# V="-v 2"

./trade_bot.py -p SOL_USD  ${V} -F data/SOL_USD_OHLC_60_20240727_20240827.csv -R "${FT}"
./trade_bot.py -p XBT_USD  ${V} -F data/XBT_USD_OHLC_60_20240727_20240827.csv -R "${FT}"
./trade_bot.py -p XDG_USD  ${V} -F data/XDG_USD_OHLC_60_20240727_20240827.csv -R "${FT}"
./trade_bot.py -p ETH_USD  ${V} -F data/ETH_USD_OHLC_60_20240727_20240827.csv -R "${FT}"

