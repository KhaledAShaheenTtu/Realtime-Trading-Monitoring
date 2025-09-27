##################################################################
#
# This is an example how getting prices from TradingView works
#
##################################################################

# Set filepaths to write historical data 
# You can also add /history/ subfolder into the path to write data into another directory
mag7_filepath = 'data/mag7_2.csv'
btcusdt_filepath = 'data/btcusdt_2.csv'
tonusdt_filepath = 'data/tonusdt_2.csv'
edgar_filepath = 'data'
news_filepath = 'data/news.csv'

# Set how many price bars (from the latest backwards) we want to retrive from the TradingView
n_bars = 500 


import requests
import pandas as pd
import logging
import time
import datetime
import os
import csv
import asyncio
import edgar_client

# Our own classes to gather some data 
from trading_data_classes import GetDataTradingView, DataWorks

tv = GetDataTradingView()
dw = DataWorks()

# from dotenv import load_dotenv  # we cannot use it cause it's not in Anaconda Base list 



def make_a_record_from_tv(symbol, exchange, interval, n_bars, file_path):
    df = tv.get_hist(           
        symbol = symbol,        #  Instrument name, format like "BTCUSDT"
        exchange = exchange,    #  Exchange, source of the quotes (from which TradingView get quotes)
                                #               format "BINANCE"
        interval = interval,    #  str value like "5" --> means 5 minutes
        n_bars = n_bars,        #  How many bars (candles) we're requesting: 
                                #               1 --> only the last one, up to 10_000 --> for history (paywall after ~10k)
    )
    # file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), file_path)
    try: 
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        write_header = False
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            write_header = True
        with open(file_path, 'a', encoding='utf-8') as f:
            if write_header:
                f.write("instrument,timestamp_utc,open_price,high_price,low_price,close_price,record_timestamp_utc\n")
            # Write all rows from the DataFrame
            for idx, row in df.iterrows():
                """
                Writing the row with the following data: 
                
                (0) exchange:instument (symbol)
                (1) candle datettime (pandas to_datetime) with the format 2025-09-13 17:30:00115905.88
                (2) open_price
                (3) high_price
                (4) low_price
                (5) close_price
                (6) record_timestamp (when the record has been put into the file)
                
                """
                f.write(f'{row.iloc[0]},'
                        f'{pd.to_datetime(idx)},'
                        f'{row.iloc[1]},{row.iloc[2]},{row.iloc[3]},{row.iloc[4]},'
                        f'{timestamp}\n')
        dw.write_log_line(text = f"{n_bars} candles of '{row.iloc[0]}' has written to {file_path} with the time {pd.to_datetime(idx)}")
    except Exception as e:
        logging.error(f"Error writing to log file: {e}")
        print(f"Error writing to log file: {e}")
    return


# Get 500 rows of every instrument (5 minutes candles)
make_a_record_from_tv(symbol = "MAG7",                                  
                      exchange = "LSE", 
                      interval = "5", 
                      n_bars = n_bars, 
                      file_path = mag7_filepath)

make_a_record_from_tv(symbol = "BTCUSDT",                                  
                        exchange = "BINANCE", 
                        interval = "5", 
                        n_bars = n_bars, 
                        file_path = btcusdt_filepath), 

make_a_record_from_tv(symbol = "TONUSDT",                                 
                        exchange = "BINANCE", 
                        interval = "5", 
                        n_bars = n_bars, 
                        file_path = tonusdt_filepath),

# Fetch latest news and write to data/news.csv (inline)
# output_csv = news_filepath

resp = requests.get(
    "https://data-api.coindesk.com/news/v1/article/list",
    params={"lang": "EN", "limit": 10, "source_ids": "coindesk", "categories": "BTC,TON"},
    headers={"Content-type": "application/json; charset=UTF-8"},
    timeout=30,
)

resp.raise_for_status()
js = resp.json()

os.makedirs(os.path.dirname(news_filepath) or '.', exist_ok=True)

with open(news_filepath, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f, quoting=csv.QUOTE_ALL)
    writer.writerow(["instrument", "utc_timestamp", "source", "raw_text"])
    for article in js.get("Data", []):
        cats = [c.get("CATEGORY") for c in article.get("CATEGORY_DATA", [])]
        instrument = "BTC" if "BTC" in cats else ("TON" if "TON" in cats else None)
        if not instrument:
            continue
        utc_ts = datetime.datetime.fromtimestamp(article["PUBLISHED_ON"], tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        source = article.get("SOURCE_DATA", {}).get("NAME", "Unknown")
        raw_text = article.get("BODY", "")
        writer.writerow([instrument, utc_ts, source, raw_text])

print(f"News written to: {os.path.abspath(news_filepath)}")


# Fetch combined SEC filings (inline) and write to data/sec_filings_combined.csv
out = edgar_client.get_and_write_combined_btc_ton_mag7(output_dir=edgar_filepath, 
                                                       btc_limit=50, 
                                                       ton_limit=50, 
                                                       mag7_limit_each=20)
print(f"SEC combined written to: {out}")