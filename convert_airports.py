#!/usr/bin/env python3
import json
import os


def convert_airport_data():
    """
    Convert the mwgg/Airports format to our application format and save to static/data/airports.json
    """
    try:
        # Ensure input file exists
        input_file = 'static/data/full_airports.json'
        if not os.path.exists(input_file):
            print(f"Error: Input file {input_file} not found")
            return False

        # Load the full airport data
        with open(input_file, 'r', encoding='utf-8') as file:
            full_airports = json.load(file)

        # Format for our application
        formatted_airports = []

        for icao_code, airport in full_airports.items():
            # Skip airports without IATA codes (less relevant)
            if not airport.get('iata') or airport['iata'] == '':
                continue

            # Create our airport format
            formatted_airport = {
                'iata': airport.get('iata', ''),
                'icao': airport.get('icao', icao_code),
                'name': airport.get('name', ''),
                'city': airport.get('city', ''),
                'country': airport.get('country', ''),
                'lat': airport.get('lat', 0),
                'lon': airport.get('lon', 0),
                'size': 'L' if airport.get('name', '').lower().find('international') > -1 else 'M'
            }

            formatted_airports.append(formatted_airport)

        # Sort by name for better usability
        formatted_airports.sort(key=lambda x: x['name'])

        # Write to output file
        output_file = 'static/data/airports.json'
        with open(output_file, 'w', encoding='utf-8') as file:
            json.dump(formatted_airports, file, indent=2, ensure_ascii=False)

        print(f"Successfully converted {len(formatted_airports)} airports to {output_file}")
        return True

    except Exception as e:
        print(f"Error converting airport data: {e}")
        return False


if __name__ == "__main__":
    convert_airport_data()
