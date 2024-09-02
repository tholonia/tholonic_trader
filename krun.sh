#!/bin/bash

# use the default values, optimizsed for 1hr

#./get_data.py -c SOL -b USD -f 2024-07-27 -t 2024-08-27 -i 60
#./get_data.py -c XBT -b USD -f 2024-07-27 -t 2024-08-27 -i 60
#./get_data.py -c XDG -b USD -f 2024-07-27 -t 2024-08-27 -i 60
#./get_data.py -c ETH -b USD -f 2024-07-27 -t 2024-08-27 -i 60

FT="2024-07-27|2024-08-27"
V="-v 101"
# V="-v 2"
L="-L 10000"

#D="SOL" ./trade_bot.py -p SOL_USD  ${V} -F data/${D}_USD_OHLC_60_20230727_20240827.csv -R "${FT}" ${L}
# D="BTC" ./trade_bot.py -p XBT_USD  ${V} -F data/XBT_USD_OHLC_60_20240727_20240827.csv -R "2023-07-27|2024-08-27" ${L}

#U="-n 1.3 -l 0.6 -c 2.4 -k 16" #~ -71.31%
U="-n 1.3 -l 0.6 -c 2.4 -k 16" #~ -71.31%

D="BTC" ./trade_bot.py -p BTC_USD  ${V} ${U}-F data/BTC_USD_OHLC_60_20230727_20240827.csv -R "2023-07-27|2024-08-27" ${L}
#D="ETH" ./trade_bot.py -p ETH_USD  ${V} -F data/${D}_USD_OHLC_60_20230727_20240827.csv  -R "${FT}" ${L}

# ./trade_bot.py -p XDG_USD  ${V} -F ${D} -R "${FT}" ${L}

