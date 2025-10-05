# Realtime-Trading-Monitoring

Our plan is to collect 6 datasets, then merge them together to extract some additional value.

## Our datasets and domains

### Domain 1. Trading prices of instruments 

* Dataset 1. BTCUSDT
* Dataset 2. TONUSDT
* Dataset 3. MAG7 

Common source: TradingView API requests. 
All the datasets consist of prices aggregated in 5-minutes 'candles' (1 candle consist of 4 prices: high, low, open, close traded during the candle interval). 


### Domain 2. SEC filings 

* Dataset 4. SEC filings

We're doing text search across SEC filings published in EDGAR database (endpoint efts.sec.gov/LATEST/search-index) looking for realted SEC filings of our instruments and indexes (BTC, TON, MAG7). See edgar_client.py for details. 

### Domain 3. FED rates 

* Dataset 5. Fed rates

We're requesting Yahoo finance API to get the latest price of ^IRX (13-week Treasury Bill). See fed_rates_screper.py for details.  

### Domain 4. News

* Dataset 6. Related news. 

We're requesting coindesk API endpoint to get the 1 latest related news for one of 3 categories (BTC, TON, MAG7). See finction fetch_and_write_news() in the file 'write_current_prices.py' to get the results. 

NOTE: currently we do not use news in the get_signal() function, just store the news for future analysis or to show them in (hypothetical) traders interface. 


## Some general notes

* It’s better to use crypto for demonstration purposes since it trades 24/7 and isn’t tied to a market calendar. We chose TradingView as our data source for the project because it provides a reasonable amount of price data without requiring authentication (no API key needed).

* Our approach is to get data without authentication wherever possible, since the code is supposed to run on several of our computers as well as on the professor’s machine.

* Our group is spread across multiple time zones, so we will stick to GMT timestamps wherever possible to avoid any inconsistencies.

##  Quick Start with Anaconda (Recommended)

### Option 1: Automated Setup
```bash
# Set up the conda environment (first time only)
./setup_environment.sh
# in case of execution on Windows it would be: 'bash ./setup_environment.sh' 
# Keep in mind in that case 'bash' has to be added into Path

# Run the application
./run_app.sh
# 'bash ./run_app.sh' in case of execution on Windows
```

### Option 2: Manual Setup
```bash
# Create conda environment from environment.yml
conda env create -f environment.yml

# Activate the environment
conda activate trading-monitor

# In case it's your first start (optional): 
# (1) execute this command (once) to retrieve 500 rows and put them down to the main file: 
python write_history_data.py
# It will request 500 last candles, latest news and SEC filings and put them into the data/ folder

# Run the main application
python write_current_price.py
```

Script is designed to run continuously to collect data every 5 minutes.


#### What does it do? 

* Waits for the next 5-minute boundary (XX:00, XX:05, XX:10, etc.).
* Then waits an additional 15 seconds to allow the quotes provider to finalize the 5-minute close.
* Requests the price from the quotes provider, receives it, and stores it in a local CSV file.
* In parallel it requests the latest news articles about 2 instruments and store it locally in data/news.csv
* In parallel, it also requests the latest SEC filings related to our trading instruments.
* After all the relevant data is gathered, it applies a small trading strategy to generate signals from the newly collected data.
* Repeats the process every 5 minutes.



##  Environment & Dependencies

### Anaconda Environment (Recommended)
This project uses Anaconda for dependency management and isolated environments.

**Key Benefits:**
-  Isolated environment prevents conflicts
-  Optimized package versions from conda-forge
-  Easy setup and reproducible environments
-  Includes Jupyter for data analysis

**Environment Details:**
- Python 3.11
- Environment name: `trading-monitor`
- All dependencies managed via `environment.yml`

### Core Dependencies
```yaml
# Data Processing
pandas>=2.0.0
numpy>=1.24.0

# Web APIs & Scraping
requests>=2.31.0

# Configuration
python-dotenv>=1.0.0

# Async programming support
aiohttp
asyncio

```


## How do we merge data:

Currently, it logs two instruments: TONUSDT and BTCUSDT. Since they share the same timestamps, you can merge them on the timestamp field — either later during analysis or directly at write time. This is the stable decision for outside_of_trading_hours demonstration purposes, because MAG7 has not trades 24/7 (API returns the last available price at the moment of market closing).


## How do we get additional value from the datasets

1) From a trading perspective, some instruments are interconnected in the market, so changes in one instrument can serve as a predictor for changes in another.
2) By continuously retrieving even small portions of data, we accumulate a valuable historical dataset that can be used for backtesting and training more complex algorithms, such as machine learning models.
3) By merging events of different types — like prices, news, and SEC filings — we can extract additional insights and make our trading signals clearer and more informative.

## Showcases 

The /experiments folder contains *.ipynb-notebooks demonstrating some of the workflows:

* data_merge_experiment.ipynb — merging data and checking it for signals
* get_history_data.ipynb — requesting 500+ rows of data to build the local history

## Licenses

We’re using only publicly available data (via APIs) and Python libraries available through pip (mostly MIT-licensed).
Some parts of the code are partially copy-pasted or inspired by other MIT-licensed libraries available in public (i.e. on Github).

All links to the source code are provided in the comments—search for 'license' to find these cases.