import requests
import pandas as pd
import datetime
import json
import os
import asyncio
from trading_data_classes import DataWorks
from config import config

class FredAPI:
    """
    Federal Reserve Economic Data (FRED) API client for fetching Fed rates
    """
    
    def __init__(self, api_key=None):
        self.base_url = "https://api.stlouisfed.org/fred"
        self.api_key = api_key or self._get_api_key()
        self.dw = DataWorks()
        
    def _get_api_key(self):
        """
        Get FRED API key from config or return demo key
        To get a free API key: https://fred.stlouisfed.org/docs/api/api_key.html
        """
        api_key = config.FRED_API_KEY
        if not api_key:
            print("⚠️  Using demo API key (limited requests)")
            print("   Get your free FRED API key at: https://fred.stlouisfed.org/docs/api/api_key.html")
            print("   Then add FRED_API_KEY='your_key_here' to your .env file")
            return "demo"  # Limited demo access
        return api_key
    
    def get_fed_funds_rate(self, limit=1):
        """
        Get Federal Funds Effective Rate
        This is the actual Fed rate set by FOMC
        """
        series_id = "FEDFUNDS"  # Federal Funds Effective Rate
        return self._fetch_series(series_id, "Federal Funds Rate", limit)
    
    def get_10year_treasury(self, limit=1):
        """
        Get 10-Year Treasury Constant Maturity Rate
        """
        series_id = "GS10"  # 10-Year Treasury Constant Maturity Rate
        return self._fetch_series(series_id, "10-Year Treasury Rate", limit)
    
    def get_3month_treasury(self, limit=1):
        """
        Get 3-Month Treasury Constant Maturity Rate
        """
        series_id = "GS3M"  # 3-Month Treasury Constant Maturity Rate
        return self._fetch_series(series_id, "3-Month Treasury Rate", limit)
    
    def get_2year_treasury(self, limit=1):
        """
        Get 2-Year Treasury Constant Maturity Rate
        """
        series_id = "GS2"  # 2-Year Treasury Constant Maturity Rate
        return self._fetch_series(series_id, "2-Year Treasury Rate", limit)
    
    def get_fed_balance_sheet(self, limit=1):
        """
        Get Fed Total Assets (Balance Sheet size)
        """
        series_id = "WALCL"  # All Federal Reserve Banks: Total Assets
        return self._fetch_series(series_id, "Fed Balance Sheet", limit)
    
    def _fetch_series(self, series_id, description, limit=1):
        """
        Fetch data from FRED API for a specific series
        """
        try:
            url = f"{self.base_url}/series/observations"
            params = {
                'series_id': series_id,
                'api_key': self.api_key,
                'file_type': 'json',
                'limit': limit,
                'sort_order': 'desc',  # Most recent first
                'output_type': 1  # Observations only
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if 'observations' not in data:
                print(f"❌ No observations data for {description}")
                return None
            
            observations = data['observations']
            if not observations:
                print(f"❌ No data points for {description}")
                return None
            
            # Convert to DataFrame
            df_data = []
            for obs in observations:
                if obs['value'] != '.':  # FRED uses '.' for missing values
                    df_data.append({
                        'date': obs['date'],
                        'rate': float(obs['value']),
                        'series_id': series_id,
                        'description': description
                    })
            
            if not df_data:
                print(f"❌ No valid data points for {description}")
                return None
            
            df = pd.DataFrame(df_data)
            df['date'] = pd.to_datetime(df['date'])
            
            return df
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error fetching {description}: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error for {description}: {e}")
            return None
        except Exception as e:
            print(f"❌ Error fetching {description}: {e}")
            return None

async def fetch_and_write_fed_rates(file_path="data/fed_rates.csv"):
    """
    Async function to fetch Fed rates and write to CSV
    Compatible with your existing asyncio structure
    """
    fred = FredAPI()
    dw = DataWorks()
    
    print("Fetching Fed rates from FRED API...")
    
    # Fetch multiple Fed rate indicators
    rates_data = {
        'fed_funds': fred.get_fed_funds_rate(),
        'treasury_10y': fred.get_10year_treasury(), 
        'treasury_3m': fred.get_3month_treasury(),
        'treasury_2y': fred.get_2year_treasury()
    }
    
    # Collect successful fetches
    successful_data = []
    for rate_name, df in rates_data.items():
        if df is not None and not df.empty:
            latest = df.iloc[0]  # Most recent
            successful_data.append({
                'instrument': rate_name,
                'rate_value': latest['rate'],
                'rate_date': latest['date'],
                'description': latest['description']
            })
            print(f"✅ {latest['description']}: {latest['rate']:.2f}% (as of {latest['date'].strftime('%Y-%m-%d')})")
    
    if not successful_data:
        print("❌ No Fed rate data retrieved")
        return
    
    # Write to CSV file
    try:
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), file_path)
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        
        # Create header if file doesn't exist
        write_header = not os.path.exists(file_path) or os.path.getsize(file_path) == 0
        
        with open(file_path, 'a', encoding='utf-8') as f:
            if write_header:
                f.write("instrument,rate_value,rate_date,description,fetch_timestamp_utc\\n")
            
            for data in successful_data:
                f.write(f"{data['instrument']},")
                f.write(f"{data['rate_value']},")
                f.write(f"{data['rate_date'].strftime('%Y-%m-%d')},")
                f.write(f"{data['description']},")
                f.write(f"{timestamp}\\n")
        
        dw.write_log_line(f"Fed rates data written: {len(successful_data)} rates to {file_path}")
        
    except Exception as e:
        print(f"❌ Error writing Fed rates to file: {e}")
        dw.write_log_line(f"Error writing Fed rates: {e}")

def test_fed_rates_endpoint():
    """
    Test the Fed rates endpoint
    """
    print("TESTING FED RATES ENDPOINT")
    print("=" * 50)
    
    fred = FredAPI()
    
    # Test different rate series
    test_series = [
        ('fed_funds', fred.get_fed_funds_rate),
        ('treasury_10y', fred.get_10year_treasury),
        ('treasury_3m', fred.get_3month_treasury),
        ('treasury_2y', fred.get_2year_treasury),
    ]
    
    print("Testing individual rate series:")
    for name, fetch_func in test_series:
        print(f"\\nTesting {name}...")
        df = fetch_func(limit=3)  # Get last 3 data points
        
        if df is not None and not df.empty:
            print(f"✅ SUCCESS!")
            print(f"   Latest rate: {df.iloc[0]['rate']:.3f}%")
            print(f"   Date: {df.iloc[0]['date'].strftime('%Y-%m-%d')}")
            print(f"   Data points: {len(df)}")
        else:
            print(f"❌ FAILED")
    
    print("\\n" + "=" * 50)
    print("TESTING ASYNC INTEGRATION")
    print("=" * 50)
    
    # Test async integration
    asyncio.run(fetch_and_write_fed_rates("data/test_fed_rates.csv"))
    
    print("\\n✅ Fed rates endpoint test completed!")
    print("\\nTo integrate with your main script, add this line:")
    print("fetch_and_write_fed_rates('data/fed_rates.csv')")

if __name__ == "__main__":
    print("FED RATES API ENDPOINT")
    print("=" * 50)
    print("This module provides access to official Federal Reserve data")
    print("via the FRED (Federal Reserve Economic Data) API")
    print()
    
    # Check for API key
    api_key = os.getenv('FRED_API_KEY')
    if not api_key:
        print("📝 SETUP INSTRUCTIONS:")
        print("1. Get free API key: https://fred.stlouisfed.org/docs/api/api_key.html")
        print("2. Set environment variable: $env:FRED_API_KEY='your_key_here'")
        print("3. Or use demo key with limited requests")
        print()
    
    test_fed_rates_endpoint()