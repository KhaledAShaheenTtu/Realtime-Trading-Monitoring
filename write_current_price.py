import requests
import pandas as pd
import logging
import time
import datetime
from trading_data_classes import GetDataTradingView, DataWorks

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

    try: 
        # timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        with open(file_path, 'a', encoding='utf-8') as f:
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
            f.write(f'{df.iloc[0:1].values[0][0]},'\
                    f'{pd.to_datetime(df.iloc[0:1].index.values[0])},'
                    f'{df.iloc[0:1].values[0][1]},{df.iloc[0:1].values[0][2]},'\
                    f'{df.iloc[0:1].values[0][3]},{df.iloc[0:1].values[0][4]},'\
                    f'{timestamp}\n'
                    )
    except Exception as e:
        logging.error(f"Error writing to log file: {e}")
        print(f"Error writing to log file: {e}")
    return


def main():
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
    dw.write_log_line(text = f'Waiting {round(delay_seconds, 1)} seconds till the next'\
                             f' 5 minutes interval before requesting price from the TradingView')
    
    time.sleep(delay_seconds)

    # When time (XX:05:15) has come --> run interatively every 5 minutes
    while True:
        make_a_record_from_tv(symbol = "BTCUSDT", exchange = "BINANCE", interval = "5", 
                              n_bars = 1,
                              file_path = 'data/btcusdt.csv')     
        dw.write_log_line(text = f"Candle of 'BTCUSDT' has written to btcusdt.csv."\
                                 f" Now I'm waiting for the next 5 minutes")

        make_a_record_from_tv(symbol = "TONUSDT", exchange = "BINANCE", interval = "5", 
                              n_bars = 1,
                              file_path = 'data/tonusdt.csv')     
        dw.write_log_line(text = f"Candle of 'TONUSDT' has written to tonusdt.csv."\
                                 f" Now I'm waiting for the next 5 minutes")

        time.sleep(300) 
        # wait 5 minutes to write next price 

if __name__ == '__main__':
    main()
