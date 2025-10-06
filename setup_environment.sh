#!/bin/bash

# Realtime Trading Monitoring Environment Setup Script
# This script sets up the conda environment from scratch

echo "Setting up Realtime Trading Monitoring Environment"
echo "====================================================="

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo "❌ Error: Conda is not installed or not in PATH"
    echo "Please install Anaconda/Miniconda first:"
    echo "  https://docs.anaconda.com/anaconda/install/"
    exit 1
fi

# Check if environment.yml exists
if [ ! -f "environment.yml" ]; then
    echo "❌ Error: environment.yml not found"
    echo "Please ensure you're in the project directory"
    exit 1
fi

# Remove existing environment if it exists
if conda env list | grep -q "trading-monitor"; then
    echo "  Removing existing trading-monitor environment..."
    conda env remove -n trading-monitor -y
fi

# Create new environment
echo " Creating new conda environment from environment.yml..."
conda env create -f environment.yml

if [ $? -eq 0 ]; then
    echo "✅ Environment created successfully!"
    
    # Source conda so we can use conda activate
    source $(conda info --base)/etc/profile.d/conda.sh
    conda activate trading-monitor
    
    echo ""
    echo "  Environment information:"
    echo "  Environment name: trading-monitor"
    echo "  Python version: $(python --version)"
    echo "  Location: $(conda info --envs | grep trading-monitor | awk '{print $2}')"
    
    echo ""
    echo " Installed packages:"
    conda list | grep -E "(pandas|numpy|requests)" || echo "Key packages are installed"
    
    echo ""
    echo "  Setup complete! You can now:"
    echo "  1. Run 'conda activate trading-monitor' to activate the environment"
    echo "  2. Or use './run_app.sh' to run the application directly"
    echo "  3. Configure your .env file with API keys if needed"
    
else
    echo "❌ Failed to create environment"
    exit 1
fi