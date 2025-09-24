import requests
import pandas as pd
import logging
import time
import datetime
import os
import csv
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Our own classes to gather some data 
from trading_data_classes import GetDataTradingView, DataWorks
from fed_rates_scraper import fetch_and_write_fed_rates_scraper
from config import config
# EDGAR client for SEC filings metadata
import edgar_client

# Creating objects of our classes 
tv = GetDataTradingView()
dw = DataWorks()


async def make_a_record_from_tv(symbol, exchange, interval, n_bars, file_path):
    df = tv.get_hist(           
        symbol = symbol,        #  Instrument name, format like "BTCUSDT"
        exchange = exchange,    #  Exchange, source of the quotes (from which TradingView get quotes)
                                #               format "BINANCE"
        interval = interval,    #  str value like "5" --> means 5 minutes
        n_bars = n_bars,        #  How many bars (candles) we're requesting: 
                                #               1 --> only the last one, up to 10_000 --> for history (paywall after ~10k)
    )
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), file_path)
    try: 
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        write_header = False
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            write_header = True
        with open(file_path, 'a', encoding='utf-8') as f:
            if write_header:
                f.write("instrument,timestamp_utc,open_price,high_price,low_price,close_price,record_timestamp_utc\n")

            # Writing all rows from the DataFrame (1 in case of 5-minutes loop execution) 
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
        dw.write_log_line(text = f"Candle of '{row.iloc[0]}' has written to {file_path}"
                                 f" with the time {pd.to_datetime(idx)}")

    except Exception as e:
        logging.error(f"Error writing to log file: {e}")
        print(f"Error writing to log file: {e}")
    return


async def fetch_and_write_news(news_limit, file_path):
    """
    Endpoint desription: 
    https://developers.coindesk.com/documentation/data-api/news_v1_article_list
    
    Provides the articles starting from the latest available in amount limited by 'news_limit' parameter 
    """
    try:
        print(f"Fetching the latest news...")
        output_csv = os.path.join(os.path.dirname(os.path.abspath(__file__)), file_path)

        # API_KEY = ""

        response = requests.get(
            "https://data-api.coindesk.com/news/v1/article/list",
            params={
                "lang": "EN",
                "limit": news_limit,
                "source_ids": "coindesk",
                "categories": "BTC,TON,MAG7",
                # "to_ts": to_ts,           # there is no need to send to_ts to get the latest articles 
                # "api_key": API_KEY,       # for some quota we do not need to provide API key, that should be enough for tests
            },
            headers={"Content-type": "application/json; charset=UTF-8"}
        )
        json_response = response.json()
        with open(output_csv, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_ALL)
            writer.writerow(["instrument", "utc_timestamp", "source", "raw_text"])
            for article in json_response.get("Data", []):
                categories = [c["CATEGORY"] for c in article.get("CATEGORY_DATA", [])]
                instrument = None
                if "BTC" in categories:
                    instrument = "BTC"
                elif "TON" in categories:
                    instrument = "TON"
                elif "MAG7" in categories:
                    instrument = "MAG7"
                if instrument:
                    utc_timestamp = datetime.datetime.fromtimestamp(article["PUBLISHED_ON"], 
                                                                    tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                    source = article.get("SOURCE_DATA", {}).get("NAME", "Unknown")
                    raw_text = article.get("BODY", "")
                    writer.writerow([instrument, utc_timestamp, source, raw_text])
        dw.write_log_line(text = f"News for instruments retrieved")

    except Exception as e:
        logging.error(f"Error writing getting news: {e}")
        print(f"Error writing getting news: {e}")
        dw.write_log_line(text = f"Getting Exception trying to fetch some news: \n{e}")
    return 


async def fetch_and_write_filings(executor=None):
    """Fetch SEC filings metadata for BTC, TON and MAG7 and write CSV files.

    Uses edgar_client.get_and_write_filings_for_keyword to perform searches and writes files
    into the `data/` folder as `sec_filings_{instrument}.csv`.
    """
    loop = asyncio.get_running_loop()
    # Run blocking network calls in a threadpool to avoid blocking event loop
    if executor is None:
        executor = ThreadPoolExecutor(max_workers=3)

    tasks = []
    # One combined CSV with instrument column and UTC filedDate
    tasks.append(loop.run_in_executor(executor, edgar_client.get_and_write_combined_btc_ton_mag7, 'data', 50, 50, 20))

    results = await asyncio.gather(*tasks)
    for r in results:
        if r:
            dw.write_log_line(text = f"EDGAR filings written to {r}")
    return


async def main(interval: float = 300.0):
    # This 'now' is only for internal loop to iteratively write prices, so this is the only place we do not convert it to GMT
    now = datetime.datetime.now()                   
    
    # Calculating how much time left before the next 5 minutes interval (XX:00, XX:05, XX:10, etc)
    minutes_to_next_5 = (5 - (now.minute % 5)) % 5 

    # We need to start 15 seconds after 5-minute round interval, because the exchange does not close candles immediately
    # It takes some seconds. So XX:05:15 (+15 seconds) should be enough
    next_5_minute_mark = now + datetime.timedelta(minutes=minutes_to_next_5)
    scheduled_time = next_5_minute_mark.replace(second=15, microsecond=0)

    # If planned time has passed -- just add 5 min more 
    if scheduled_time <= now:
        scheduled_time += datetime.timedelta(minutes=5)

    # Delay to the next start time
    delay_seconds = (scheduled_time - now).total_seconds()
    dw.write_log_line(text = f'Waiting {round(delay_seconds, 1)} seconds till the next'
                             f' 5 minutes interval before requesting price from the TradingView')
    await asyncio.sleep(delay_seconds)  # instead of time.sleep() we now have to use asyncio version

    # Entering the 5 minutes loop (with substraction of execution time)
    loop = asyncio.get_running_loop()
    next_run = loop.time()  # стартовая «фаза» сейчас

    while True:
        # Executing the tasks (coroutines in terms of asyncio) in parallel using asyncio.gather(task1, task2... taskN)
        await asyncio.gather(make_a_record_from_tv(symbol = "BTCUSDT",                                  # Coroutine 1: Write price of BTCUSDT 
                                                   exchange = "BINANCE", interval = "5", n_bars = 1, 
                                                   file_path = config.BTCUSDT_FILE), 
                             make_a_record_from_tv(symbol = "TONUSDT",                                  # Coroutine 2: Write price of TONUSDT
                                                   exchange = "BINANCE", interval = "5", n_bars = 1, 
                                                   file_path = config.TONUSDT_FILE),
                             make_a_record_from_tv(symbol = "MAG7",                                     # Coroutine 3: Write price of MAG7
                                                   exchange = "LSE", interval = "5", n_bars = 1, 
                                                   file_path = config.MAG7_FILE),
                             fetch_and_write_fed_rates_scraper(file_path=config.FED_RATES_FILE),        # Coroutine 4: Fetch Fed rates from Yahoo Finance
                             fetch_and_write_news(news_limit=config.NEWS_FETCH_LIMIT, file_path=config.NEWS_FILE), # Coroutine 5: Fetching news 
                             fetch_and_write_filings()                                                  # Coroutine 6: Fetch SEC filings metadata
                            )

        # We can also execute any function AFTER asyncio.gather() finished like that: 
        # await fetch_and_write_news(news_limit, file_path = 'data/news.csv')       
       
        dw.write_log_line(text = f"Gathering prices, Fed rates, news and filings has finished, Now I'm waiting for the next 5 minutes...")

        next_run += interval
        now = loop.time()
        if now > next_run: # in case execution was longer than the whole interval -- skip next run 
            missed = int((now - next_run) // interval) + 1
            next_run += missed * interval

        dw.write_log_line(f"Wait time till the next start: {round(max(0.0, next_run - loop.time()), 1)}")
        await asyncio.sleep(max(0.0, next_run - loop.time()))   # wait 300 seconds minus execution time till the next run

if __name__ == '__main__':
    # Print configuration summary
    print("REALTIME TRADING MONITORING")
    print("=" * 50)
    config.print_config_summary()
    print("\n" + "=" * 50)
    print("STARTING DATA COLLECTION...")
    print("=" * 50)
    
    asyncio.run(main(config.COLLECTION_INTERVAL))
