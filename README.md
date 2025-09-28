# Realtime-Trading-Monitoring

Our plan is to collect 4 datasets, then merge them together to extract some additional value.

## Our datasets and domains

### Domain 1. Trading prices of instruments 

Common source: TradingView API requests. 

* Dataset 1. BTCUSDT
* Dataset 2. TONUSDT
* Dataset 3. MAG7 

### Domain 2. SEC filings 

* Dataset 4. SEC filings

### Domain 3. FED rates 

* Dataset 5. Fer rates

### Domain 4. News

* Dataset 6. Related news. 



#### Some general notes

* It’s better to use crypto for demonstration purposes, since it trades 24/7 and doesn’t depend on a market calendar. We chose TradingView as our quotes source for the project because it provides reasonable amoung of price data without any authentication (no API key required).

* Our approach is try to get data without authentications all where it's possible, cause the code supposed to run on a several of our computers and should also run on a professors machine.

* Our group are spread across timezones, so we will stick to GMT timestamps wherever possible to avoid any inconsistency

## 🚀 Quick Start with Anaconda (Recommended)

### Option 1: Automated Setup
```bash
# Set up the conda environment (first time only)
./setup_environment.sh

# Run the application
./run_app.sh
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

Script is designed to run continuously to collect data every 5 minutes. See TODO section for improvements.

What does it do? 

* Waits for the next 5-minute boundary (XX:00, XX:05, XX:10, etc.).
* Then waits an additional 15 seconds to allow the exchange to finalize the 5-minute close.
* Requests the price from the exchange, receives it, and stores it in a local CSV file.
* In parallel it requests the latest news articles about 2 instruments and store it locally in data/news.csv

How to merge:

Currently, it logs two instruments: TONUSDT and BTCUSDT. Since they share the same timestamps, you can merge them on the timestamp field—either later during analysis or directly at write time.


## Part 1. Trading prices of instruments 

To be done 


## Part 2. News 

To be done 


## Part 3. Regulatory documents and releases

To be done 


## 📦 Environment & Dependencies

### Anaconda Environment (Recommended)
This project uses Anaconda for dependency management and isolated environments.

**Key Benefits:**
- 🔒 Isolated environment prevents conflicts
- 📦 Optimized package versions from conda-forge
- 🚀 Easy setup and reproducible environments
- 🧪 Includes Jupyter for data analysis

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
beautifulsoup4>=4.12.0
lxml>=4.9.0
websocket-client>=1.6.0

# Configuration
python-dotenv>=1.0.0

# Analysis Tools
jupyter, matplotlib, seaborn, plotly
```



### TODO: 

1) Merge of all data sources to the current signal generation logic