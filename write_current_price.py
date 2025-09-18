import requests
import pandas as pd
import logging
import time
import datetime
import os
import csv
from trading_data_classes import GetDataTradingView, DataWorks
from dotenv import load_dotenv

tv = GetDataTradingView()
dw = DataWorks()


def make_a_record_from_tv(symbol, exchange, interval, n_bars, file_path):
    df = tv.get_hist(           
        symbol = symbol,        #  Instrument name, format like "BTCUSDT"
        exchange = exchange,    #  Exchange, source of the quotes (from which TradingView get quotes)
                                #               format "BINANCE"
        interval = interval,    #  str value like "5" --> means 5 minutes
        n_bars = n_bars,        #  How many bars (candles) we're requesting: 
                                #               1 --> only the last one, up to 10_000 --> for history
    )
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), file_path)

    try: 
        # timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        write_header = False
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            write_header = True
        with open(file_path, 'a', encoding='utf-8') as f:
            if write_header:
                f.write("instrument,timestamp_utc,open_price,high_price,low_price,close_price,record_timestamp_utc\n")
            """
            writing the row with the following data: 
                (0) exchange:instument (symbol)
                (1) candle datettime (pandas to_datetime) with the format 2025-09-13 17:30:00115905.88
                (2) open_price
                (3) high_price
                (4) low_price
                (5) close_price
                (6) record_timestamp (when the record has been put into the file)
            """
            f.write(f'{df.iloc[0:1].values[0][0]},'
                    f'{pd.to_datetime(df.iloc[0:1].index.values[0])},'
                    f'{df.iloc[0:1].values[0][1]},{df.iloc[0:1].values[0][2]},'
                    f'{df.iloc[0:1].values[0][3]},{df.iloc[0:1].values[0][4]},'
                    f'{timestamp}\n'
                    )
            return pd.to_datetime(df.iloc[0:1].index.values[0])
    except Exception as e:
        logging.error(f"Error writing to log file: {e}")
        print(f"Error writing to log file: {e}")
    return


def fetch_and_write_news(to_ts, news_limit, file_path):
    try:
        print(to_ts)
        output_csv = os.path.join(os.path.dirname(os.path.abspath(__file__)), file_path)
        load_dotenv()
        
        API_KEY = os.getenv("COINDESK_API_KEY")
        response = requests.get(
            "https://data-api.coindesk.com/news/v1/article/list",
            params={
                "lang": "EN",
                "limit": news_limit,
                "source_ids": "coindesk",
                "categories": "BTC,TON",
                "to_ts": to_ts,
                "api_key": API_KEY,
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
                if instrument:
                    utc_timestamp = datetime.datetime.fromtimestamp(article["PUBLISHED_ON"], tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                    source = article.get("SOURCE_DATA", {}).get("NAME", "Unknown")
                    raw_text = article.get("BODY", "")
                    writer.writerow([instrument, utc_timestamp, source, raw_text])

    except Exception as e:
        logging.error(f"Error writing getting news: {e}")
        print(f"Error writing getting news: {e}")

def main():
    news_limit = 2
    now = datetime.datetime.now()
    minutes_to_next_5 = (5 - (now.minute % 5)) % 5 
    # How much time left before the next 5 minutes interval (XX:00, XX:05, XX:10, etc)

    # We need to start 15 seconds after 5-minute round interval, 
    #           because the exchange does not close candles exact after 5 minutes closed
    # It usually takes several seconds. XX:05:15 (+15 seconds) should be enough
    next_5_minute_mark = now + datetime.timedelta(minutes=minutes_to_next_5)
    scheduled_time = next_5_minute_mark.replace(second=15, microsecond=0)

    # If planned time has passed -- just add 5 min more 
    if scheduled_time <= now:
        scheduled_time += datetime.timedelta(minutes=5)

    # Delay to the next start time
    delay_seconds = (scheduled_time - now).total_seconds()
    dw.write_log_line(text = f'Waiting {round(delay_seconds, 1)} seconds till the next'
                             f' 5 minutes interval before requesting price from the TradingView')
    
    time.sleep(delay_seconds)

    while True:
        make_a_record_from_tv(symbol = "BTCUSDT", exchange = "BINANCE", interval = "5", 
                              n_bars = 1,
                              file_path = 'data/btcusdt.csv')     
        dw.write_log_line(text = f"Candle of 'BTCUSDT' has written to btcusdt.csv."
                                 f" Now I'm waiting for the next 5 minutes")

        returned_timestamp = make_a_record_from_tv(symbol = "TONUSDT", exchange = "BINANCE", interval = "5", 
                              n_bars = 1,
                              file_path = 'data/tonusdt.csv')     
        
        dw.write_log_line(text = f"Candle of 'TONUSDT' has written to tonusdt.csv."
                                 f" Now I'm waiting for the next 5 minutes")
        fetch_and_write_news(int(returned_timestamp.timestamp()), news_limit, file_path = 'data/news.csv')
        dw.write_log_line(text = f"News for BTCUSDT and TONUSDT retrieved from timestamp: {returned_timestamp} Now I'm waiting for the next 5 minutes")
        time.sleep(300) # wait 5 minutes to write next price 

if __name__ == '__main__':
    main() 
