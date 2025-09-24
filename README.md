# Realtime-Trading-Monitoring

Our plan is to collect 4 datasets, then merge them together to extract some value.

## Part 1. Price for several instruments from the exchange

It’s better to use crypto, since it trades 24/7 and doesn’t depend on a market calendar. We chose Binance because it provides price data without authentication (no API key required).

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

# Run the application
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


### TODO: 

1) With current approach there will be small data drift cause our tasks takes several seconds, so in total it's not exact 300, its about 303-307 seconds for every 5 minutes. That would be great to make a single Loop to count the time above asyncio.gather() execution

2) To replace 'create_connection from websocket' with local functions to fit project guidelines

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

