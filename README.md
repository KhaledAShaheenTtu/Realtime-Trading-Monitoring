# Realtime-Trading-Monitoring


Our plan is to collect 4 datasets, then merge them together to extract some value.

## Part 1. Price for several instruments from the exchange

It’s better to use crypto, since it trades 24/7 and doesn’t depend on a market calendar. We chose Binance because it provides price data without authentication (no API key required).

You can start the script from the console as follows:

```python
python .\write_current_price.py
```

Script supposed to be running all time  to write enough rows (1 row per 5 min). See TODO section.

What does it do? 

* Waits for the next 5-minute boundary (XX:00, XX:05, XX:10, etc.).
* Then waits an additional 15 seconds to allow the exchange to finalize the 5-minute close.
* Requests the price from the exchange, receives it, and stores it in a local CSV file.
* In parallel it requests the latest news articles about 2 instruments and store it locally in data/news.csv

How to merge:

Currently, it logs two instruments: TONUSDT and BTCUSDT. Since they share the same timestamps, you can merge them on the timestamp field—either later during analysis or directly at write time.


### TODO: 

1) With current approach there will be small data drift cause our tasks takes several seconds, so in total it's not exact 300, its about 303-307 seconds for every 5 minutes. That would be great to make a single Loop to count the time above asyncio.gather() execution

2) To replace 'create_connection from websocket' with local functions to fit project guidelines

## Part 2. News 

To be done 


## Part 3. Regulatory documents and releases

To be done 


## Dependencies

Python modules (lastest versions as of 2025-09-10):

```python 
logging
time
datetime
json
random
re
string
pandas

# Could be out of stardard Conda package, but could be installed from Conda
requests
websocket
```
