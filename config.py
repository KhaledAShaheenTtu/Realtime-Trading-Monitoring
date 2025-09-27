"""
Configuration module for Realtime Trading Monitoring
Loads environment variables from .env file
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

class Config:
    """Configuration class to centralize all environment variables"""
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE_PATH = os.getenv('LOG_FILE_PATH', 'data/logs.csv')
    
    # Data Collection Settings
    COLLECTION_INTERVAL = int(os.getenv('COLLECTION_INTERVAL', '300'))
    NEWS_FETCH_LIMIT = int(os.getenv('NEWS_FETCH_LIMIT', '1'))
    # SEC Filings limits
    FILINGS_BTC_LIMIT = int(os.getenv('FILINGS_BTC_LIMIT', '50'))
    FILINGS_TON_LIMIT = int(os.getenv('FILINGS_TON_LIMIT', '50'))
    FILINGS_MAG7_EACH_LIMIT = int(os.getenv('FILINGS_MAG7_EACH_LIMIT', '20'))
    
    # File Paths
    DATA_DIR = os.getenv('DATA_DIR', 'data')
    BTCUSDT_FILE = os.getenv('BTCUSDT_FILE', 'data/btcusdt.csv')
    TONUSDT_FILE = os.getenv('TONUSDT_FILE', 'data/tonusdt.csv')
    MAG7_FILE = os.getenv('MAG7_FILE', 'data/mag7.csv')
    FED_RATES_FILE = os.getenv('FED_RATES_FILE', 'data/fed_rates.csv')
    NEWS_FILE = os.getenv('NEWS_FILE', 'data/news.csv')
    FILINGS_FILE = os.getenv('FILINGS_FILE', 'data/sec_filings_combined.csv')
    SIGNALS_FILE = os.getenv('SIGNALS_FILE', 'data/signals.csv')

    # API Rate Limiting
    FRED_RATE_LIMIT = int(os.getenv('FRED_RATE_LIMIT', '120'))
    YAHOO_FINANCE_RATE_LIMIT = int(os.getenv('YAHOO_FINANCE_RATE_LIMIT', '2000'))
    
    # Retry Configuration
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
    RETRY_DELAY = int(os.getenv('RETRY_DELAY', '5'))
    
    # Environment
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
    
    @classmethod
    def is_development(cls):
        """Check if running in development mode"""
        return cls.ENVIRONMENT.lower() == 'development'
    
    @classmethod
    def is_production(cls):
        """Check if running in production mode"""
        return cls.ENVIRONMENT.lower() == 'production'
    
    @classmethod
    def get_api_key(cls, service_name):
        """Get API key for a specific service"""
        service_keys = {
            'fred': cls.FRED_API_KEY,
            'alpha_vantage': cls.ALPHA_VANTAGE_API_KEY,
            'coindesk': cls.COINDESK_API_KEY
        }
        return service_keys.get(service_name.lower(), '')
    
    @classmethod
    def validate_config(cls):
        """Validate configuration and return missing required keys"""
        missing_keys = []
        warnings = []
        
        # Check for optional API keys (warnings only)
        if not cls.FRED_API_KEY:
            warnings.append("FRED_API_KEY not set - using demo/fallback sources")
        
        if not cls.ALPHA_VANTAGE_API_KEY:
            warnings.append("ALPHA_VANTAGE_API_KEY not set - limited access")
        
        # Check data directory exists
        if not os.path.exists(cls.DATA_DIR):
            try:
                os.makedirs(cls.DATA_DIR)
                print(f"✅ Created data directory: {cls.DATA_DIR}")
            except Exception as e:
                missing_keys.append(f"Cannot create data directory {cls.DATA_DIR}: {e}")
        
        return missing_keys, warnings
    
    @classmethod
    def print_config_summary(cls):
        """Print a summary of current configuration"""
        print("CONFIGURATION SUMMARY")
        print("=" * 50)
        print(f"Environment: {cls.ENVIRONMENT}")
        print(f"Data Directory: {cls.DATA_DIR}")
        print(f"Collection Interval: {cls.COLLECTION_INTERVAL}s")
        print(f"Log Level: {cls.LOG_LEVEL}")
        
        
        print(f"\nData Files:")
        print(f"  BTC/USDT: {cls.BTCUSDT_FILE}")
        print(f"  TON/USDT: {cls.TONUSDT_FILE}")
        print(f"  MAG7: {cls.MAG7_FILE}")
        print(f"  Fed Rates: {cls.FED_RATES_FILE}")
        print(f"  News: {cls.NEWS_FILE}")
        print(f"  SEC Filings: {cls.FILINGS_FILE}")
        print(f"\nFilings Limits:")
        print(f"  BTC limit: {cls.FILINGS_BTC_LIMIT}")
        print(f"  TON limit: {cls.FILINGS_TON_LIMIT}")
        print(f"  MAG7 per CIK limit: {cls.FILINGS_MAG7_EACH_LIMIT}")

# Create a global config instance
config = Config()

if __name__ == "__main__":
    print("ENVIRONMENT CONFIGURATION TEST")
    print("=" * 50)
    
    # Validate configuration
    missing, warnings = config.validate_config()
    
    if missing:
        print("❌ MISSING REQUIRED CONFIGURATION:")
        for item in missing:
            print(f"  • {item}")
        print()
    
    if warnings:
        print("⚠️ CONFIGURATION WARNINGS:")
        for warning in warnings:
            print(f"  • {warning}")
        print()
    
    if not missing:
        print("✅ Configuration validation passed!")
        print()
    
    # Print configuration summary
    config.print_config_summary()
    
    print("\n" + "=" * 50)
    print("SETUP INSTRUCTIONS")
    print("=" * 50)
    print("1. Copy .env.example to .env (already done)")
    print("2. Edit .env file with your API keys:")
    print("3. Restart your application to reload configuration")