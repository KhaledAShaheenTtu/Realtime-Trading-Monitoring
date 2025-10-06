#!/bin/bash

# Realtime Trading Monitoring Application Launcher
# This script activates the conda environment and runs the main application

echo "Starting Realtime Trading Monitoring Application"
echo "=================================================="

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo "❌ Error: Conda is not installed or not in PATH"
    echo "Please install Anaconda/Miniconda first"
    exit 1
fi

# Check if trading-monitor environment exists
if ! conda env list | grep -q "trading-monitor"; then
    echo "❌ Error: trading-monitor environment not found"
    echo "Please run setup_environment.sh first"
    exit 1
fi

# Source conda so we can use conda activate
source $(conda info --base)/etc/profile.d/conda.sh

# Activate the conda environment
echo "🔧 Activating conda environment: trading-monitor"
conda activate trading-monitor

# Check if activation was successful
if [ "$CONDA_DEFAULT_ENV" != "trading-monitor" ]; then
    echo "❌ Error: Failed to activate trading-monitor environment"
    exit 1
fi

echo "✅ Environment activated successfully"

# Display current configuration
echo "📋 Checking configuration..."
python config.py

echo ""
echo "🏃 Starting the trading monitor application..."
echo "Press Ctrl+C to stop the application"
echo ""

# Run the main application
python write_current_price.py