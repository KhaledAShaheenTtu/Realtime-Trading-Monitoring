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

How to merge:

Currently, it logs two instruments: TONUSDT and BTCUSDT. Since they share the same timestamps, you can merge them on the timestamp field—either later during analysis or directly at write time.


### TODO for Part 1: 

1) For now the timestamps of the price is from the exchange (so they are alligned to each other), but they're writing in local timezone of the machine requesting price. It's better to convert timestamps to GMT cause we're in different timezones and that could be asking for trouble to store them in local time. 

2) For now in case of skip for any reason we're going to have ommited data. That would be great to add functionality to fullfill the gaps by request of operator and in the background (in case of network issues and skip of 1 record row). 

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

# Could be out of stardard Conda package, but could be installed from Conda
requests
pandas
websocket
```
