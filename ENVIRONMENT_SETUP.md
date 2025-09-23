# Environment Configuration Guide

## ✅ .env File Successfully Added!

This project now uses environment variables for configuration management, making it more secure and flexible.

## 🔧 Setup Instructions

### 1. Environment Variables File
The project includes:
- `.env.example` - Template with all available settings
- `.env` - Your actual configuration (already created)
- `config.py` - Configuration module that loads .env values

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure API Keys (Optional but Recommended)

#### FRED API (Federal Reserve Data) - Free
```bash
# 1. Get free API key: https://fred.stlouisfed.org/docs/api/api_key.html
# 2. Add to .env file:
FRED_API_KEY=your_actual_fred_api_key_here
```

#### Alpha Vantage API - Free Tier Available
```bash
# 1. Get free API key: https://www.alphavantage.co/support/#api-key
# 2. Add to .env file:
ALPHA_VANTAGE_API_KEY=your_actual_alpha_vantage_key_here
```

## 📊 Current Configuration

### Data Collection Settings
```env
COLLECTION_INTERVAL=300     # 5 minutes between collections
NEWS_FETCH_LIMIT=1         # Number of news articles per fetch
LOG_LEVEL=INFO             # Logging verbosity
ENVIRONMENT=development    # development or production
```

### File Paths (Configurable)
```env
DATA_DIR=data
BTCUSDT_FILE=data/btcusdt.csv
TONUSDT_FILE=data/tonusdt.csv
MAG7_FILE=data/mag7.csv
FED_RATES_FILE=data/fed_rates.csv
NEWS_FILE=data/news.csv
FILINGS_FILE=data/sec_filings_combined.csv
```

### API Rate Limits
```env
FRED_RATE_LIMIT=120           # Requests per minute
YAHOO_FINANCE_RATE_LIMIT=2000 # Requests per minute
MAX_RETRIES=3                 # Retry attempts on failure
RETRY_DELAY=5                 # Seconds between retries
```

## 🚀 Usage

### Test Configuration
```bash
python config.py
```

### Run Main Application
```bash
python write_current_price.py
```

The application will now:
1. Load configuration from .env file
2. Display configuration summary on startup
3. Use configured file paths and settings
4. Handle API keys securely

## 🔒 Security Features

✅ **API Keys Protected**: Stored in .env file (excluded from git)  
✅ **Default Fallbacks**: Works without API keys using free sources  
✅ **Environment Separation**: Different configs for dev/prod  
✅ **Validation**: Checks configuration on startup  

## 📁 File Structure
```
├── .env                    # Your actual configuration
├── .env.example           # Configuration template
├── config.py              # Configuration loader
├── requirements.txt       # Python dependencies
├── write_current_price.py # Main application (updated)
├── fed_rates_api.py       # Fed rates (updated)
├── fed_rates_scraper.py   # Fed rates scraper (updated)
└── data/                  # Data output directory
```

## 🔧 Customization

### Change Data Collection Interval
Edit `.env` file:
```env
COLLECTION_INTERVAL=600  # 10 minutes instead of 5
```

### Change File Locations
Edit `.env` file:
```env
DATA_DIR=my_data
BTCUSDT_FILE=my_data/bitcoin_prices.csv
```

### Production Mode
Edit `.env` file:
```env
ENVIRONMENT=production
LOG_LEVEL=ERROR
```

## ⚠️ Important Notes

1. **Never commit .env file** - It's already in .gitignore
2. **API keys are optional** - The system works with fallback sources
3. **Configuration is validated** - Missing critical settings are reported
4. **Paths are auto-created** - Data directories are created automatically

## 🛠️ Troubleshooting

### "Module not found" error
```bash
pip install python-dotenv
```

### Configuration not loading
1. Check `.env` file exists in project root
2. Run `python config.py` to validate
3. Ensure no extra quotes around values

### API key not working
1. Verify key is correct in `.env` file
2. Check API service status
3. Fallback sources will be used automatically

Your environment configuration is now fully set up and integrated! 🎉