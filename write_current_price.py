import requests
import pandas as pd
import logging
import datetime
import os
import csv
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Our own classes to gather some data 
from trading_data_classes import GetDataTradingView, DataWorks, Strategy
from fed_rates_scraper import fetch_and_write_fed_rates_scraper
from config import config
# EDGAR client for SEC filings metadata
import edgar_client

# Creating objects of our classes 
tv = GetDataTradingView()
dw = DataWorks()
s = Strategy()

async def make_a_record_from_tv(symbol, exchange, interval, n_bars, file_path):
    df = tv.get_hist(           
        symbol = symbol,        #  Instrument name, format like "BTCUSDT"
        exchange = exchange,    #  Exchange, source of the quotes (from which TradingView get quotes)
                                #               format "BINANCE"
        interval = interval,    #  str value like "5" --> means 5 minutes
        n_bars = n_bars,        #  How many bars (candles) we're requesting: 
                                #               1 --> only the last one, up to 10_000 --> for history (paywall after ~10k)
    )
    full_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), file_path)
    try: 
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        write_header = False
        if not os.path.exists(full_file_path) or os.path.getsize(full_file_path) == 0:
            write_header = True
        with open(full_file_path, 'a', encoding='utf-8') as f:
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
        dw.write_log_line(text = f"Candle of '{row.iloc[0]}' has written to the file {file_path} with the time {pd.to_datetime(idx)}")

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
        # Resolve output path relative to this file if not absolute
        output_csv = file_path if os.path.isabs(file_path) else os.path.join(os.path.dirname(os.path.abspath(__file__)), file_path)

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
        # Determine whether to write header
        write_header = (not os.path.exists(output_csv)) or os.path.getsize(output_csv) == 0
        with open(output_csv, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_ALL)
            if write_header:
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


def _resolve_path(p: str) -> str:
    return p if os.path.isabs(p) else os.path.join(os.path.dirname(os.path.abspath(__file__)), p)


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
    # One combined CSV with instrument column and UTC filedDate. Use config for limits and output path.
    output_file = _resolve_path(config.FILINGS_FILE)
    tasks.append(
        loop.run_in_executor(
            executor,
            edgar_client.get_and_write_combined_btc_ton_mag7,
            config.DATA_DIR,
            config.FILINGS_BTC_LIMIT,
            config.FILINGS_TON_LIMIT,
            config.FILINGS_MAG7_EACH_LIMIT,
            output_file,
            True,
            True,
        )
    )

    results = await asyncio.gather(*tasks)
    for r in results:
        if r:
            dw.write_log_line(text = f"EDGAR filings written to:  {r[-29:]}") # last 29 symbols of path
    return


async def get_signal(file_path):
    """
    After gathering all the data we can try to generate signal (indicator to buy or sell)
    
    How we're getting signal: 
    
    (1) We're reading last 500 rows of just updated CSV files with BTC and TON latest prices
    (2) Merging them on the timestamp_utc 
    (3) Applying our trading strategy (s.apply_values_for_double_strat()) for both instruments 
    (4) Check the last row if it has any signal (value = 1) in any of traget variables ('buy_signal_btc' etc.)
    (5) If the last (current) price returns signal, we're recording that into signals.csv file

    """
    dw.write_log_line(text = f"Trying to check the last data for signal")

    def _load_price_frame(path: str, suffix: str) -> pd.DataFrame:
        resolved = _resolve_path(path)
        if not os.path.exists(resolved):
            return pd.DataFrame()
        df = pd.read_csv(resolved).tail(500)
        if df.empty:
            return df
        df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'], utc=True, errors='coerce')
        df = df.sort_values('timestamp_utc').drop_duplicates('timestamp_utc')
        rename_map = {col: f"{col}_{suffix}" for col in df.columns if col != 'timestamp_utc'}
        return df.rename(columns=rename_map)

    def _load_fed_rates() -> pd.DataFrame:
        resolved = _resolve_path(config.FED_RATES_FILE)
        if not os.path.exists(resolved):
            return pd.DataFrame()
        df = pd.read_csv(resolved)
        if df.empty:
            return df
        df['fetch_timestamp_utc'] = pd.to_datetime(df['fetch_timestamp_utc'], utc=True, errors='coerce')
        df = df.sort_values('fetch_timestamp_utc').drop_duplicates('fetch_timestamp_utc', keep='last')
        return df[['fetch_timestamp_utc', 'rate_value', 'description']]

    def _load_news() -> pd.DataFrame:
        resolved = _resolve_path(config.NEWS_FILE)
        if not os.path.exists(resolved):
            return pd.DataFrame()
        df = pd.read_csv(resolved)
        if df.empty:
            return df
        df['utc_timestamp'] = pd.to_datetime(df['utc_timestamp'], utc=True, errors='coerce')
        df = df.sort_values('utc_timestamp').drop_duplicates(['instrument', 'utc_timestamp'], keep='last')
        return df

    def _load_filings() -> pd.DataFrame:
        resolved = _resolve_path(config.FILINGS_FILE)
        if not os.path.exists(resolved):
            return pd.DataFrame()
        df = pd.read_csv(resolved)
        if df.empty:
            return df
        df['filedDate'] = pd.to_datetime(df['filedDate'], utc=True, errors='coerce')
        df = df.dropna(subset=['filedDate'])
        df = df.sort_values('filedDate').drop_duplicates(['instrument', 'accessionNumber'], keep='last')
        return df

    def _attach_latest_event(base_df: pd.DataFrame, events_df: pd.DataFrame, instrument: str,
                              time_col: str, prefix: str, rename_cols: dict, direction: str = 'backward') -> pd.DataFrame:
        if base_df.empty:
            return base_df
        time_column_name = f"{prefix}_time"
        value_columns = list(rename_cols.values())
        hours_column = f"{prefix}_hours_since"
        if events_df.empty or 'instrument' not in events_df.columns or instrument not in events_df['instrument'].unique():
            base_df[time_column_name] = pd.NaT
            for col in value_columns:
                base_df[col] = pd.NA
            base_df[hours_column] = pd.NA
            return base_df
        subset = events_df[events_df['instrument'] == instrument].copy()
        if subset.empty:
            base_df[time_column_name] = pd.NaT
            for col in value_columns:
                base_df[col] = pd.NA
            base_df[hours_column] = pd.NA
            return base_df
        subset = subset.sort_values(time_col)
        keep_cols = [time_col] + list(rename_cols.keys())
        subset = subset[keep_cols]
        merged = pd.merge_asof(
            base_df.sort_values('timestamp_utc'),
            subset,
            left_on='timestamp_utc',
            right_on=time_col,
            direction=direction,
        )
        merged = merged.rename(columns={time_col: time_column_name, **rename_cols})
        if time_column_name in merged.columns:
            merged[hours_column] = (
                (merged['timestamp_utc'] - merged[time_column_name]).dt.total_seconds() / 3600.0
            )
        else:
            merged[hours_column] = pd.NA
        return merged

    try:
        df_btc = _load_price_frame(config.BTCUSDT_FILE, 'btc')
        df_ton = _load_price_frame(config.TONUSDT_FILE, 'ton')
        df_mag7 = _load_price_frame(config.MAG7_FILE, 'mag7')

        if df_btc.empty or df_ton.empty:
            raise ValueError('Insufficient price data to compute signals.')

        df_merged = df_btc.merge(df_ton, on='timestamp_utc', how='inner')
        if not df_mag7.empty:
            df_merged = df_merged.merge(df_mag7, on='timestamp_utc', how='left')

        df_merged = df_merged.sort_values('timestamp_utc')

        # Attach Fed rate information (latest known rate prior to timestamp)
        fed_rates = _load_fed_rates()
        if not fed_rates.empty:
            df_merged = pd.merge_asof(
                df_merged,
                fed_rates,
                left_on='timestamp_utc',
                right_on='fetch_timestamp_utc',
                direction='backward'
            )
            df_merged = df_merged.rename(columns={
                'fetch_timestamp_utc': 'fed_rate_timestamp',
                'rate_value': 'fed_rate_value',
                'description': 'fed_rate_description'
            })
            df_merged['fed_rate_value'] = df_merged['fed_rate_value'].ffill()
        else:
            df_merged['fed_rate_timestamp'] = pd.NaT
            df_merged['fed_rate_value'] = pd.NA
            df_merged['fed_rate_description'] = pd.NA

        # Attach latest news per instrument
        news_df = _load_news()
        df_merged = _attach_latest_event(
            df_merged,
            news_df,
            'BTC',
            'utc_timestamp',
            'btc_news',
            {'source': 'btc_news_source', 'raw_text': 'btc_news_raw_text'}
        )
        df_merged = _attach_latest_event(
            df_merged,
            news_df,
            'TON',
            'utc_timestamp',
            'ton_news',
            {'source': 'ton_news_source', 'raw_text': 'ton_news_raw_text'}
        )
        df_merged = _attach_latest_event(
            df_merged,
            news_df,
            'MAG7',
            'utc_timestamp',
            'mag7_news',
            {'source': 'mag7_news_source', 'raw_text': 'mag7_news_raw_text'}
        )

        # Attach latest SEC filing per instrument
        filings_df = _load_filings()
        df_merged = _attach_latest_event(
            df_merged,
            filings_df,
            'BTC',
            'filedDate',
            'btc_filing',
            {
                'companyName': 'btc_filing_company',
                'form': 'btc_filing_form',
                'detail_url': 'btc_filing_detail_url'
            }
        )
        df_merged = _attach_latest_event(
            df_merged,
            filings_df,
            'TON',
            'filedDate',
            'ton_filing',
            {
                'companyName': 'ton_filing_company',
                'form': 'ton_filing_form',
                'detail_url': 'ton_filing_detail_url'
            }
        )
        df_merged = _attach_latest_event(
            df_merged,
            filings_df,
            'MAG7',
            'filedDate',
            'mag7_filing',
            {
                'companyName': 'mag7_filing_company',
                'form': 'mag7_filing_form',
                'detail_url': 'mag7_filing_detail_url'
            }
        )

        # Apply trading strategy on enriched frame
        df_merged = s.apply_values_for_double_strat(df_merged, 'close_price_btc', 'btc')
        df_merged = s.apply_values_for_double_strat(df_merged, 'close_price_ton', 'ton')

        last_row = df_merged.tail(1)
        signal_condition = (
            (last_row['buy_signal_btc'] > 0) |
            (last_row['buy_signal_ton'] > 0) |
            (last_row['sell_signal_btc'] > 0) |
            (last_row['sell_signal_ton'] > 0)
        ).any()

        if signal_condition:
            last_row[['instrument_btc','timestamp_utc','open_price_btc','high_price_btc',
            'low_price_btc','close_price_btc','record_timestamp_utc_btc','instrument_ton',
            'open_price_ton','high_price_ton','low_price_ton','close_price_ton',
            'record_timestamp_utc_ton','RSI_dd_strat','BB_basis','BB_upper',
            'BB_lower','buy_signal_btc','sell_signal_btc','buy_signal_ton','sell_signal_ton']].to_csv(file_path, mode='a', header=not os.path.exists(file_path), index=False)
            print('Signal row written to signals.csv')
        else:
            print('No signal in the last row')
    except Exception as e:
        dw.write_log_line(text = f"Unsuccessfull signal check with Exception: \n {e}")

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
    
    # Comment this out this raw for immidiate start (skip wait for 1st round interval)
    await asyncio.sleep(delay_seconds)  # instead of time.sleep() we now have to use asyncio version

    # Entering the 5 minutes loop (with substraction of execution time)
    loop = asyncio.get_running_loop()
    next_run = loop.time()  # start phase is now

    while True:
        # Executing the tasks (coroutines in terms of asyncio) in parallel using asyncio.gather(task1, task2... taskN)
        await asyncio.gather(# Coroutine 1: Write price of BTCUSDT 
                            make_a_record_from_tv(symbol = "BTCUSDT",                                  
                                                   exchange = "BINANCE", interval = "5", n_bars = 1, 
                                                   file_path = config.BTCUSDT_FILE),                        
                            # Coroutine 2: Write price of TONUSDT
                            make_a_record_from_tv(symbol = "TONUSDT",                                  
                                                   exchange = "BINANCE", interval = "5", n_bars = 1, 
                                                   file_path = config.TONUSDT_FILE),
                            # Coroutine 3: Write price of MAG7
                            make_a_record_from_tv(symbol = "MAG7",                                    
                                                   exchange = "LSE", interval = "5", n_bars = 1, 
                                                   file_path = config.MAG7_FILE),
                            # Coroutine 4: Fetch Fed rates from Yahoo Finance              
                            fetch_and_write_fed_rates_scraper(file_path=config.FED_RATES_FILE, range_value=config.FED_RATES_RANGE, interval=config.FED_RATES_INTERVAL),    
                            # Coroutine 5: Fetching news                             
                            fetch_and_write_news(news_limit=config.NEWS_FETCH_LIMIT, file_path=config.NEWS_FILE), 
                            # Coroutine 6: Fetch SEC filings metadata                                                 
                            fetch_and_write_filings() 
                            )

        # When all the data gathered we can use it for some merge and predictions: 
        await get_signal(file_path=config.SIGNALS_FILE)

        dw.write_log_line(text = f"{'='*50} \nGathering prices, Fed rates, news and filings has finished, Now I'm waiting for the next 5 minutes... \n{'='*50} ")

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
