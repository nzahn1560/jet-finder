import pandas as pd
import json
import os
import uuid
from datetime import datetime


def clean_numeric(value):
    """Convert numeric values to proper format, handling special characters like $, commas, etc."""
    if isinstance(value, str):
        # Remove $ and commas
        value = value.replace('$', '').replace(',', '')
        # Remove quotation marks
        value = value.replace('"', '')

    try:
        # Try to convert to float
        return float(value)
    except (ValueError, TypeError):
        # If conversion fails, return original value
        return value


def get_category(aircraft_type):
    """Determine aircraft category based on type field"""
    if isinstance(aircraft_type, str):
        aircraft_type = aircraft_type.lower()
        if 'jet' in aircraft_type:
            return 'jet'
        elif 'turboprop' in aircraft_type:
            return 'turboprop'
        elif 'piston' in aircraft_type:
            return 'piston'
    return 'piston'  # Default to piston if unknown


def main():
    # Check if CSV file exists
    csv_path = 'Aircraft Data - Aircraft Data (1).csv'
    if not os.path.exists(csv_path):
        print(f"Error: CSV file '{csv_path}' not found.")
        return

    # Read the CSV file
    try:
        # Skip the first row which contains header description
        # Use first row as data, set column names to indices
        df = pd.read_csv(csv_path, header=None)
        print(f"Successfully read CSV with {len(df) - 1} rows")

        # Get column names from the first row (for reference)
        column_names = df.iloc[0].tolist()

        # Remove the header row from the dataframe
        df = df.iloc[1:].reset_index(drop=True)

        # Print the column names for reference
        print(f"Column names from CSV: {column_names[:10]}...")
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return

    # Create directory for data if it doesn't exist
    os.makedirs('data', exist_ok=True)

    # Check if listings.json exists and read existing listings
    listings_path = 'data/listings.json'
    existing_listings = []
    if os.path.exists(listings_path):
        try:
            with open(listings_path, 'r') as f:
                existing_listings = json.load(f)
            print(f"Loaded {len(existing_listings)} existing listings")
        except Exception as e:
            print(f"Error loading existing listings: {e}")
            existing_listings = []

    # Column indices for relevant data (based on the header row)
    col_idx = {
        'aircraft_name': 0,  # First column contains aircraft model name
        'manufacturer': 1,   # Second column is manufacturer
        'type': 2,           # Third column is aircraft type
        'min_year': 4,       # Fifth column is lowest year
        'max_year': 5,       # Sixth column is highest year
        'max_altitude': 11,  # Max operating altitude
        'range': 23,         # Range in NM
        'speed': 24,         # Speed in KTS
        'passengers': 25,    # Number of passengers
        'price': 26,         # Average price
        'total_hourly_cost': 58,  # Total hourly cost
        'hourly_variable_cost': 62,  # Hourly variable cost
        'annual_budget': 37  # Annual budget
    }

    # Process each row in the CSV and convert to listing format
    new_listings = []
    for idx, row in df.iterrows():
        # Skip rows without an aircraft name (first column)
        if pd.isna(row[col_idx['aircraft_name']]):
            continue

        # Get aircraft name from first column
        aircraft_name = row[col_idx['aircraft_name']]

        # Get manufacturer from second column or from aircraft name
        manufacturer = row[col_idx['manufacturer']] if not pd.isna(
            row[col_idx['manufacturer']]) else aircraft_name.split(' ')[0]

        # Get model from aircraft name, removing manufacturer if it's a prefix
        if aircraft_name.startswith(manufacturer):
            model = aircraft_name[len(manufacturer):].strip()
        else:
            model = aircraft_name

        # Determine aircraft type and category
        aircraft_type = row[col_idx['type']] if not pd.isna(row[col_idx['type']]) else 'Piston'
        category = get_category(aircraft_type)

        # Determine year range
        try:
            min_year = int(float(row[col_idx['min_year']])) if not pd.isna(row[col_idx['min_year']]) else 2000
            max_year = int(float(row[col_idx['max_year']])) if not pd.isna(row[col_idx['max_year']]) else min_year + 5

            # Use middle of the year range
            year = min_year + (max_year - min_year) // 2
        except (ValueError, TypeError):
            # Default if years can't be parsed
            min_year = 2000
            max_year = 2010
            year = 2005

        # Get price
        price = clean_numeric(row[col_idx['price']]) if not pd.isna(row[col_idx['price']]) else 0

        # Get performance data
        try:
            range_nm = int(float(row[col_idx['range']])) if not pd.isna(row[col_idx['range']]) else 0
            max_speed = int(float(row[col_idx['speed']])) if not pd.isna(row[col_idx['speed']]) else 0
            seats = int(float(row[col_idx['passengers']])) if not pd.isna(row[col_idx['passengers']]) else 0
            max_altitude = int(float(row[col_idx['max_altitude']])) if not pd.isna(
                row[col_idx['max_altitude']]) else 25000
        except (ValueError, TypeError):
            range_nm = 0
            max_speed = 0
            seats = 0
            max_altitude = 25000

        # Get operating costs if available
        hourly_cost = clean_numeric(row[col_idx['total_hourly_cost']]) if not pd.isna(
            row.get(col_idx['total_hourly_cost'], '')) else 0
        hourly_variable_cost = clean_numeric(row[col_idx['hourly_variable_cost']]) if not pd.isna(
            row.get(col_idx['hourly_variable_cost'], '')) else 0
        annual_budget = clean_numeric(row[col_idx['annual_budget']]) if not pd.isna(
            row.get(col_idx['annual_budget'], '')) else 0

        # Create a listing
        listing = {
            "id": str(uuid.uuid4()),
            "title": f"{year} {manufacturer} {model}",
            "category": category,
            "manufacturer": manufacturer,
            "model": model,
            "year": year,
            "description": f"{year} {manufacturer} {model} {aircraft_type}. Range: {range_nm} nm, Max Speed: {max_speed} kts, Seats: {seats}.",
            "price": int(price),
            "total_time": int(500 + (2023 - year) * 100),  # Estimate total time based on age
            "registration": f"N{str(abs(hash(aircraft_name)))[:4]}",
            "serial": f"{model[:3].upper()}-{str(abs(hash(aircraft_name)))[:4]}",
            "location": "Various Locations",
            "engines": f"{manufacturer} {aircraft_type} Engine",
            "engine_hours": f"{int(500 + (2023 - year) * 100)}",
            "programs": "Varies",
            "avionics": "Standard",
            "max_speed": max_speed,
            "range": range_nm,
            "service_ceiling": max_altitude,
            "seats": seats,
            "images": [
                f"{category.lower()}_placeholder.jpg"
            ],
            "seller_id": "system_import",
            "seller_name": "Jet Finder Database",
            "created_at": datetime.now().isoformat(),
            "status": "active",
            "featured": False,
            "hourly_cost": hourly_cost,
            "hourly_variable_cost": hourly_variable_cost,
            "annual_budget": annual_budget
        }

        new_listings.append(listing)

    print(f"Created {len(new_listings)} new listings from CSV data")

    # Combine existing and new listings, avoiding duplicates
    all_listings = existing_listings.copy()

    # Add new listings, checking for duplicates based on manufacturer and model
    existing_models = {f"{listing['manufacturer']} {listing['model']}".lower() for listing in existing_listings}

    for listing in new_listings:
        listing_key = f"{listing['manufacturer']} {listing['model']}".lower()
        if listing_key not in existing_models:
            all_listings.append(listing)
            existing_models.add(listing_key)

    print(f"Total listings after merging: {len(all_listings)}")

    # Save combined listings to JSON file
    try:
        with open(listings_path, 'w') as f:
            json.dump(all_listings, f, indent=2)
        print(f"Successfully saved {len(all_listings)} listings to {listings_path}")
    except Exception as e:
        print(f"Error saving listings: {e}")


if __name__ == "__main__":
    main()
