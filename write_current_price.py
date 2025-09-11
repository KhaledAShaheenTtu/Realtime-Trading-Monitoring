import requests
import pandas as pd
import logging
import time
from datetime import datetime, timedelta


def write_log_line(text, file_path=f'data/logs.csv'):
    try: 
        logging.info(f'{text}')
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(f'{timestamp} {text}\n')
            print(text)                                 # to also show in console 
    except Exception as e:
        logging.error(f"Error writing to log file: {e}")
        print(f"Error writing to log file: {e}")
    return


def convert_timestamp_to_iso(timestamp):
    dt = datetime.fromtimestamp(timestamp / 1000.0)    # Convert to datetime timestamp 
    return dt.strftime('%Y-%m-%d %H:%M:%S.%f')         # Convert to ISO timestamt 


def make_a_record_from_binance(symbol, csvname, limit=2):
    """
    Makes a request to API of Binance exchange to get the price of the instrument.
    Always returns first candle before last one. 

    Supposed to start with limit=2 to get last filled candle from binance.
    Records LOCAL time of candles in format '2024-12-30 11:55:00.000000'
    """
    
    interval = '5m'  # We're collecting 5 minutes candles, so this is our interval to wait between requests
    
    # Request to Binance API to get the last closed candle
    # Returns the last candle (not closed one), so we need previous one (which is closed and price is stable), that's why limit=2 
    url = f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}'

    response = requests.get(url)
    last_candel = []
    
    if response.status_code == 200:
        data = response.json()
        last_candle = data[0]   # last candle is [1], but [0] is the last _closed_ candle (where price is finalized and won't change anymore) 
        open_time = last_candle[0]
        open_price = float(last_candle[1])
        high_price = float(last_candle[2])
        low_price = float(last_candle[3])
        close_price = float(last_candle[4])
        volume = float(last_candle[5])
        close_time = last_candle[6]
    
        last_candel.append({'close_time': convert_timestamp_to_iso(close_time), 
                            'record_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'),
                            'close': close_price,
                            'open': open_price,
                            'high': high_price,
                            'low': low_price,
                            'Volume': volume,
                            'time': convert_timestamp_to_iso(open_time)
                            })
        last_candel_df = pd.DataFrame(last_candel)

    else:
        print(f"Failed to retrieve data: {response.status_code}")
        write_log_line(f"!_! CANNOT WRITE CANDLE. Failed to retrieve data")
    
    candles = pd.read_csv(f'data/{csvname}.csv')
    candles_upd = pd.concat([candles, last_candel_df]).copy()
    candles_upd.to_csv(f'data/{csvname}.csv', index=False)
    write_log_line(f"CANDLE {symbol} was written TO {csvname}.csv. So life is good")
    return close_time, close_price


def main():
    now = datetime.now()
    minutes_to_next_5 = (5 - (now.minute % 5)) % 5 # How much time before the next 5 minutes interval (XX:00, XX:05, XX:10, etc)

    # We need to start 15 seconds after 5-minute round interval, because the exchange does not close candles exact after 5 minutes closed
    # It usually takes several seconds. XX:05:15 (+15 seconds) should be enough
    next_5_minute_mark = now + timedelta(minutes=minutes_to_next_5)
    scheduled_time = next_5_minute_mark.replace(second=15, microsecond=0)

    # If planned time has passed -- just add 5 min more 
    if scheduled_time <= now:
        scheduled_time += timedelta(minutes=5)

    # Delay to the next start time
    delay_seconds = (scheduled_time - now).total_seconds()
    write_log_line(f'Waiting {round(delay_seconds, 1)} till the next 5 minutes before requesting price from the exchange')

    time.sleep(delay_seconds)

    # When time (XX:05:15) has come -- run interatively every 5 minutes
    while True:
        make_a_record_from_binance(symbol='TONUSDT', csvname='tonusdt')
        write_log_line(f"Candle of 'TONUSDT' has written to tonusdt.csv. Now I'm waiting for the next 5 minutes")
        make_a_record_from_binance(symbol='BTCUSDT', csvname='btcusdt')
        write_log_line(f"Candle of 'BTCUSDT' has written to tonusdt.csv. Now I'm waiting for the next 5 minutes")
        
        time.sleep(300)                     # wait 5 minutes to write next price 


if __name__ == '__main__':
    main()
