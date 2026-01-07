#!/bin/bash

# Setup script for importing aircraft data from CSV to the Jet Finder application

echo "Setting up aircraft data import..."

# Check if python3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

# Check if pip is installed
if ! command -v pip &> /dev/null && ! command -v pip3 &> /dev/null; then
    echo "Error: pip is required but not installed."
    exit 1
fi

# Determine pip command (pip or pip3)
PIP_CMD="pip"
if command -v pip3 &> /dev/null; then
    PIP_CMD="pip3"
fi

# Install pandas if not already installed
echo "Checking for pandas..."
python3 -c "import pandas" 2>/dev/null || {
    echo "Installing pandas..."
    $PIP_CMD install pandas
}

# Check if the CSV file exists
if [ ! -f "Aircraft Data - Aircraft Data (1).csv" ]; then
    echo "Error: CSV file 'Aircraft Data - Aircraft Data (1).csv' not found."
    exit 1
fi

# Create data directory if it doesn't exist
mkdir -p data

# Run the import script
echo "Running aircraft data import script..."
python3 import_aircraft_data.py

# Check if import was successful
if [ $? -eq 0 ]; then
    echo "Data import completed successfully."
    echo "Check data/listings.json for the imported data."
    
    # Count the number of listings
    LISTING_COUNT=$(python3 -c "import json; print(len(json.load(open('data/listings.json'))))")
    echo "Total listings in database: $LISTING_COUNT"
    
    echo "You can now run the Jet Finder application to see the imported data."
else
    echo "Error: Data import failed."
    exit 1
fi

echo "Setup complete!" 