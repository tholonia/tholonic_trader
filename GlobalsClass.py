import pandas as pd
import datetime

last_buy_date_list = [datetime.datetime.fromtimestamp(0.0)]
last_sell_date_list = [datetime.datetime.fromtimestamp(0.0)]
last_buy_price_list = []
positions = 0
trades_list = []
trade_counter = 0
cum_return = 0
cum_overhodl = 0

