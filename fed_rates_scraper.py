import requests
import datetime
import os
import asyncio
from trading_data_classes import DataWorks
from config import config

class FedRatesScaper:
    """
    Alternative Fed rates data collector using public data sources
    No API key required
    """
    
    def __init__(self):
        self.dw = DataWorks()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def get_fed_funds_rate_yahoo(self):
        """
        Get Fed Funds rate from Yahoo Finance
        Symbol: ^IRX (13-week Treasury Bill)
        """
        try:
            # Yahoo Finance API endpoint for Treasury data
            url = "https://query1.finance.yahoo.com/v8/finance/chart/^IRX"
            params = {
                'interval': '1d',
                'range': '5d'
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
    
    def get_all_available_rates(self):
        """
        Try multiple sources and return all successful fetches
        """
        # print("Fetching Fed rates from multiple sources...")
        
        sources = [
            ('Yahoo Finance', self.get_fed_funds_rate_yahoo)
        ]
        
        successful_rates = []
        
        for source_name, fetch_func in sources:
            try:
                print(f"Trying {source_name}...")
                rate_data = fetch_func()
                
                if rate_data:
                    print(f"{source_name}: {rate_data['rate']:.3f}% ({rate_data['description']})")
                    successful_rates.append(rate_data)
                else:
                    print(f"❌ {source_name}: No data")
                    
            except Exception as e:
                print(f"❌ {source_name}: Error - {e}")
        
        return successful_rates

async def fetch_and_write_fed_rates_scraper(file_path="data/fed_rates_scraper.csv"):
    """
    Async function to fetch Fed rates using scraping and write to CSV
    """
    scraper = FedRatesScaper()
    dw = DataWorks()
    
    print("Fetching Fed rates from public sources (no API key needed)...")
    
    # Get rates from all available sources
    rates_data = scraper.get_all_available_rates()
    
    if not rates_data:
        print("❌ No Fed rate data retrieved from any source")
        return
    
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
        
        dw.write_log_line(f"Fed rates scraped and written: {len(rates_data)} sources to the file: {file_path}")
        print(f"Successfully wrote {len(rates_data)} Fed rate sources to {file_path}")
        
    except Exception as e:
        print(f"❌ Error writing Fed rates to file: {e}")
        dw.write_log_line(f"Error writing Fed rates: {e}")

def test_fed_rates_scraper():
    """
    Test the Fed rates scraper
    """
    print("TESTING FED RATES SCRAPER")
    print("=" * 50)
    print("This method uses public data sources - no API key needed!")
    print()
    
    scraper = FedRatesScaper()
    
    # Test all sources
    rates = scraper.get_all_available_rates()
    
    print(f"\n📊 RESULTS SUMMARY:")
    print("=" * 50)
    
    if rates:
        print(f"✅ Successfully fetched Fed rate data from {len(rates)} sources:")
        
        for rate_data in rates:
            print(f"   • {rate_data['source']}: {rate_data['rate']:.3f}%")
            print(f"     {rate_data['description']}")
        
        print(f"\n🔄 TESTING ASYNC INTEGRATION:")
        asyncio.run(fetch_and_write_fed_rates_scraper("data/test_fed_rates_scraper.csv"))
        
    else:
        print("❌ No Fed rate data sources working")
        print("This could be due to:")
        print("• Website structure changes")
        print("• Network connectivity issues") 
        print("• Rate limiting from sources")
    
    print(f"\n✅ Fed rates scraper test completed!")

if __name__ == "__main__":
    print("FED RATES SCRAPER ENDPOINT")
    print("=" * 50)
    print("Alternative Fed rates data collection using public sources")
    print("No API key registration required!")
    print()
    
    test_fed_rates_scraper()