# Environment Configuration Guide

## 🚀 Anaconda Environment Setup (Recommended)

This project has been refactored to use Anaconda for optimal dependency management and environment isolation.

### Quick Setup
```bash
# Automated setup (recommended)
./setup_environment.sh

# Or manual setup
conda env create -f environment.yml
conda activate trading-monitor
```

### Benefits of Using Anaconda
- ✅ **Isolated Environment**: No conflicts with system Python
- ✅ **Optimized Packages**: Pre-compiled binaries from conda-forge
- ✅ **Reproducible**: Same environment across different machines
- ✅ **Jupyter Integration**: Built-in support for data analysis
- ✅ **Easy Management**: Simple activate/deactivate workflow

## ✅ .env File Successfully Added!

This project now uses environment variables for configuration management, making it more secure and flexible.

## 🔧 Setup Instructions

### 1. Environment Variables File
The project includes:
- `.env.example` - Template with all available settings
- `.env` - Your actual configuration (already created)
- `config.py` - Configuration module that loads .env values

### 2. Environment Setup

```bash
# Automated setup (recommended)
./setup_environment.sh

# Run the application
./run_app.sh

# Or manual steps
conda activate trading-monitor
python write_current_price.py
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

```bash
# Quick start - runs everything automatically
./run_app.sh

# Or step by step
conda activate trading-monitor
python config.py          # Test configuration
python write_current_price.py  # Run main application
```


### What the Application Does:
1. Load configuration from .env file
2. Activate the optimized conda environment
3. Display configuration summary on startup
4. Use configured file paths and settings
5. Handle API keys securely
6. Collect data every 5 minutes automatically

## 🔒 Security Features

✅ **API Keys Protected**: Stored in .env file (excluded from git)  
✅ **Default Fallbacks**: Works without API keys using free sources  
✅ **Environment Separation**: Different configs for dev/prod  
✅ **Validation**: Checks configuration on startup  

## 📁 File Structure
```
├── .env                    # Your actual configuration
├── .env.example           # Configuration template
├── environment.yml        # Conda environment specification
├── config.py              # Configuration loader
├── setup_environment.sh   # Automated environment setup
├── run_app.sh             # Application launcher
├── write_current_price.py # Main application
├── fed_rates_scraper.py   # Fed rates scraper
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

### Anaconda Issues

#### Environment not found
```bash
# List available environments
conda env list

# Recreate if missing
./setup_environment.sh
```

#### "conda: command not found"
```bash
# Initialize conda in your shell
conda init zsh  # or bash
# Restart terminal
```

#### Activation script fails
```bash
# Make scripts executable
chmod +x run_app.sh setup_environment.sh

# Or run manually
conda activate trading-monitor
python write_current_price.py
```

#### "Module not found" error
```bash
# Ensure conda environment is activated
conda activate trading-monitor
```

### Configuration Issues
1. Check `.env` file exists in project root
2. Run `python config.py` to validate
3. Ensure no extra quotes around values
4. Verify conda environment is activated

Your environment configuration is now fully set up and integrated! 🎉