import os
import requests
import pandas as pd
import logging
import time
from datetime import datetime, timedelta, timezone

LOG_PATH = 'data/logs.csv'

def iso_utc_now_ms() -> str:
    # e.g., 2025-09-11T20:05:00.123Z
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')

def iso_utc_from_ms_epoch(ms_epoch: int) -> str:
    dt = datetime.fromtimestamp(ms_epoch / 1000.0, tz=timezone.utc)
    return dt.isoformat(timespec='milliseconds').replace('+00:00', 'Z')

def write_log_line(text: str, file_path: str = LOG_PATH):
    try:
        logging.info(text)
        timestamp = iso_utc_now_ms()
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(f'{timestamp} {text}\n')
        print(text)  # optional console echo
    except Exception as e:
        logging.error(f"Error writing to log file: {e}")
        print(f"Error writing to log file: {e}")

def ensure_csv(path: str, columns: list[str]):
    # Create the CSV with headers if it doesn't exist
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        pd.DataFrame(columns=columns).to_csv(path, index=False)

def make_a_record_from_binance(symbol: str, csvname: str, limit: int = 2):
    """
    Fetch last CLOSED 5m candle from Binance and append a UTC/GMT row to data/{csvname}.csv.
    All timestamps are UTC in ISO-8601 (milliseconds) with trailing 'Z'.
    """
    interval = '5m'
    url = f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}'

    resp = requests.get(url, timeout=20)
    if resp.status_code != 200:
        msg = f"Failed to retrieve data for {symbol}: HTTP {resp.status_code}"
        print(msg)
        write_log_line(f"!_! {msg}")
        return None, None

    data = resp.json()
    if not data:
        write_log_line(f"!_! Empty data for {symbol}")
        return None, None

    # Index 0 = last CLOSED candle when limit=2 (Binance returns the last two, last is still-forming)
    last_candle = data[0]
    open_time_ms = last_candle[0]
    open_price = float(last_candle[1])
    high_price = float(last_candle[2])
    low_price = float(last_candle[3])
    close_price = float(last_candle[4])
    volume = float(last_candle[5])
    close_time_ms = last_candle[6]

    row = {
        'close_time': iso_utc_from_ms_epoch(close_time_ms),
        'record_time': iso_utc_now_ms(),            # when WE recorded the row
        'close': close_price,
        'open': open_price,
        'high': high_price,
        'low': low_price,
        'volume': volume,
        'open_time': iso_utc_from_ms_epoch(open_time_ms)
    }

    csv_path = f'data/{csvname}.csv'
    columns = ['open_time', 'close_time', 'record_time', 'open', 'high', 'low', 'close', 'volume']
    ensure_csv(csv_path, columns)

    try:
        candles_upd = pd.concat([pd.read_csv(csv_path), pd.DataFrame([row], columns=columns)], ignore_index=True)
        candles_upd.to_csv(csv_path, index=False)
        write_log_line(f"CANDLE {symbol} wrote to {csvname}.csv.")
    except Exception as e:
        write_log_line(f"!_! Failed to write {symbol} to {csvname}.csv: {e}")
        return None, None

    return close_time_ms, close_price

def main():
    now = datetime.now(timezone.utc)
    minutes_to_next_5 = (5 - (now.minute % 5)) % 5
    next_5_minute_mark = now + timedelta(minutes=minutes_to_next_5)
    scheduled_time = next_5_minute_mark.replace(second=15, microsecond=0)

    if scheduled_time <= now:
        scheduled_time += timedelta(minutes=5)

    delay_seconds = (scheduled_time - now).total_seconds()
    write_log_line(f'Waiting {round(delay_seconds, 1)}s to the next 5-minute boundary (UTC).')
    time.sleep(delay_seconds)

    while True:
        make_a_record_from_binance(symbol='TONUSDT', csvname='tonusdt')
        write_log_line("Candle for TONUSDT written to tonusdt.csv. Waiting 5 minutes.")
        make_a_record_from_binance(symbol='BTCUSDT', csvname='btcusdt')
        write_log_line("Candle for BTCUSDT written to btcusdt.csv. Waiting 5 minutes.")

        time.sleep(300)

if __name__ == '__main__':
    main()
