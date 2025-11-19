#!/bin/bash
# Script to activate the virtual environment

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv venv
    echo "Installing requirements..."
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    playwright install chromium
    echo "Setup complete!"
else
    source venv/bin/activate
    echo "Virtual environment activated!"
fi