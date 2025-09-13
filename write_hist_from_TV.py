##################################################################
#
# This is an example how getting prices from TradingView works
#
##################################################################

import pandas as pd

# Ensure current directory is in sys.path for imports (to avoid import errors)
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our project code from the nearest file trading_data_classes.py
from trading_data_classes import GetDataTradingView
tv = GetDataTradingView()


df = tv.get_hist(
        symbol = "BTCUSDT",           # Instrument name
        exchange = "BINANCE",         # Exchange, source of the quotes 
        interval = "5",               # 5 minutes
        n_bars = 1,                   # How many bars (candles) we're requesting: 
                                      #  1 -- only the last one, 500 -- full history
        # fut_contract = 2,           # Special, do not use with basic instruments 
        # extended_session = False,   # Special, do not use with basic instruments 
    )

print(df.head(10))


##### RETURNS: ######
# print(pd.to_datetime(df.iloc[0:1].index.values[0])) # datetime of the candle 
# print(df.iloc[0:1].values[0][0]) # BINANCE:BTCUSDT
# print(df.iloc[0:1].values[0][1]) # open
# print(df.iloc[0:1].values[0][2]) # high
# print(df.iloc[0:1].values[0][3]) # low
# print(df.iloc[0:1].values[0][4]) # close
# print(df.iloc[0:1].values[0][1]) # volume
