import requests
import datetime
import os
from trading_data_classes import DataWorks
from config import config

class FedRatesScaper:    
    def __init__(self):
        self.dw = DataWorks()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def get_fed_funds_rate_yahoo(self, range_value: str = '1h', interval: str = '5m'):
        """
        Get Fed Funds rate from Yahoo Finance
        Symbol: ^IRX (13-week Treasury Bill)
        """
        try:
            # Yahoo Finance API endpoint for Treasury data
            url = "https://query1.finance.yahoo.com/v8/finance/chart/^IRX"
            params = {
                'interval': interval, # e.g. '5m'
                'range': range_value   # e.g. '1h'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if 'chart' in data and data['chart']['result']:
                result = data['chart']['result'][0]
                if 'meta' in result and 'regularMarketPrice' in result['meta']:
                    current_rate = result['meta']['regularMarketPrice']
                    return {
                        'rate': current_rate,
                        'source': 'Yahoo Finance ^IRX',
                        'description': '13-Week Treasury Bill Rate',
                        'timestamp': datetime.datetime.now(datetime.timezone.utc)
                    }
            
            return None
            
        except Exception as e:
            print(f"❌ Error fetching from Yahoo Finance: {e}")
            return None

async def fetch_and_write_fed_rates_scraper(file_path="data/fed_rates_scraper.csv", range_value: str = None, interval: str = None):
    """
    Async function to fetch Fed rates using scraping and write to CSV
    """
    scraper = FedRatesScaper()
    dw = DataWorks()
    
    # Get rates from all available sources. Pass range/interval if provided
    if range_value is None:
        range_value = config.FED_RATES_RANGE
    if interval is None:
        interval = config.FED_RATES_INTERVAL

    # Attempt to use the yahoo fetcher with provided params
    rates_data = []
    try:
        y = scraper.get_fed_funds_rate_yahoo(range_value=range_value, interval=interval)
        if isinstance(y, list):
            rates_data.extend(y)
        elif y:
            rates_data.append(y)
    except Exception as e:
        print(f"Error fetching from Yahoo with params range={range_value} interval={interval}: {e}")
    
    # Write to CSV file
    try:
        full_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), file_path)
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        
        # Create header if file doesn't exist
        write_header = not os.path.exists(full_file_path) or os.path.getsize(full_file_path) == 0
        
        with open(full_file_path, 'a', encoding='utf-8') as f:
            if write_header:
                f.write("source,rate_value,description,fetch_timestamp_utc\n")
            
            for rate_data in rates_data:
                f.write(f"{rate_data['source']},")
                f.write(f"{rate_data['rate']:.4f},")
                f.write(f"{rate_data['description']},")
                f.write(f"{timestamp}\n")
        
        dw.write_log_line(f"Fed rates scraped and written from yahoo: {file_path}")
        print(f"Successfully wrote to {file_path}")
        
    except Exception as e:
        print(f"❌ Error writing Fed rates to file: {e}")
        dw.write_log_line(f"Error writing Fed rates: {e}")