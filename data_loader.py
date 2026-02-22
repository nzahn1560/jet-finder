"""
Load aircraft and airport data from files. Used by db.py for seeding PostgreSQL/SQLite.
"""
import json
from pathlib import Path

import pandas as pd


def _safe_int(value, default=0):
    if pd.isna(value):
        return default
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        cleaned = value.replace(',', '').replace('$', '').replace('%', '').strip()
        try:
            return int(float(cleaned))
        except (ValueError, TypeError):
            return default
    return default


def _safe_float(value, default=0.0):
    if pd.isna(value):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace(',', '').replace('$', '').replace('%', '').strip()
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return default
    return default


def _generate_performance_profile(aircraft):
    required = [
        'price', 'range', 'speed', 'passengers', 'year',
        'total_hourly_cost', 'runway_length', 'max_altitude',
        'cabin_volume', 'baggage_volume', 'depreciation_rate',
        'best_speed_dollar', 'best_range_dollar', 'best_performance_dollar',
        'best_efficiency_dollar', 'best_all_around_dollar'
    ]
    for m in required:
        v = aircraft.get(m)
        if v is None or v == '' or (isinstance(v, (int, float)) and v == 0):
            raise ValueError(f"Missing or invalid: {m}")
    return {m: aircraft.get(m) for m in required}


def load_aircraft_from_csv(path):
    """Load aircraft from CSV, return list of dicts (same shape as app expects)."""
    df = pd.read_csv(path)
    out = []
    for _, row in df.iterrows():
        aircraft = {
            'id': len(out) + 1,
            'aircraft_name': str(row.get('316', 'Unknown')),
            'manufacturer': str(row.get('Manufacturer', 'Unknown')),
            'model': str(row.get('316', 'Unknown')),
            'year': _safe_int(row.get('Highest Year'), 2020),
            'price': _safe_int(row.get('Average Price')),
            'range': _safe_int(row.get('Range(NM)')),
            'speed': _safe_int(row.get('Speed(KTS)')),
            'passengers': _safe_int(row.get('Passengers')),
            'category': str(row.get('Type', 'Unknown')),
            'location': 'Various Locations',
            'description': f"{row.get('Manufacturer', 'Unknown')} {row.get('Type', 'Unknown')} - {row.get('Date Range', 'Unknown years')}",
            'image': '/static/images/aircraft_placeholder.jpg',
            'date_range': str(row.get('Date Range', '')),
            'lowest_year': _safe_int(row.get('Lowest Year')),
            'highest_year': _safe_int(row.get('Highest Year')),
            'max_altitude': _safe_int(row.get('Max Operating Altitude (ft)')),
            'runway_length': _safe_int(row.get('Balanced Field Length (ft)')),
            'aircraft_height': _safe_float(row.get('Aircraft Height (ft)')),
            'wingspan': _safe_float(row.get('Wingspan (ft)')),
            'aircraft_length': _safe_float(row.get('Aircraft Length (ft)')),
            'aircraft_volume': _safe_int(row.get('Aircraft Volume (cubic ft)')),
            'cabin_height': _safe_float(row.get('Cabin Height (ft)')),
            'cabin_width': _safe_float(row.get('Cabin Width (ft)')),
            'cabin_length': _safe_float(row.get('Cabin Length (ft)')),
            'cabin_volume': _safe_float(row.get('Cabin Volume (cubic ft)')),
            'baggage_volume': _safe_int(row.get('Baggage Volume (cubic ft)')),
            'charter_rate': _safe_float(row.get('Hourly Charter Rate')),
            'total_hourly_cost': _safe_float(row.get('Total Hourly Cost')),
            'years_range': str(row.get('Date Range', 'Unknown')),
            'multi_engine': str(row.get('Multi Engine', 'Unknown')),
            'min_crew': _safe_int(row.get('Min Crew Required'), 1),
            'depreciation_rate': _safe_float(row.get('Depreciation Rate')),
            'average_trip_time': _safe_float(row.get('Average Trip Time')),
            'total_trip_time': _safe_float(row.get('# of Hours')),
            'annual_budget': _safe_float(row.get('Annual Budget')),
            'adjusted_annual_budget': _safe_float(row.get('Adjusted Annual Budget')),
            'multi_year_total_cost': _safe_float(row.get('Multi-Year Total Cost')),
            'mytc_with_aircraft_sale': _safe_float(row.get('MYTC w/ Aircraft Sale')),
            'cost_to_charter': _safe_float(row.get('Cost To Charter')),
            'total_fixed_cost': _safe_float(row.get('Total Fixed Cost')),
            'total_variable_cost': _safe_float(row.get('Total Variable Cost')),
            'adjusted_variable_cost': _safe_float(row.get('Adjusted Variable Cost')),
            'own_charter_ratio': _safe_float(row.get('Own/Charter Ratio')),
            'own_charter_savings': _safe_float(row.get('Own/Charter Savings')),
            'best_speed_dollar': _safe_float(row.get('Best Speed/$')),
            'normalized_speed_dollar': _safe_float(row.get('Normalized Speed/$')),
            'best_seat_speed_dollar': _safe_float(row.get('Best Seat Speed/$')),
            'best_range_dollar': _safe_float(row.get('Best Range/$')),
            'normalized_range_dollar': _safe_float(row.get('Normalized Range/$')),
            'best_seat_range_dollar': _safe_float(row.get('Best Seat Range/$')),
            'best_performance_dollar': _safe_float(row.get('Best Performance/$')),
            'normalized_performance_dollar': _safe_float(row.get('Normalized Performance/$')),
            'best_seat_performance_dollar': _safe_float(row.get('Best Seat Performance/$')),
            'best_efficiency_dollar': _safe_float(row.get('Best Efficiency/$')),
            'normalized_efficiency_dollar': _safe_float(row.get('Normalized Effieciency/$')),
            'best_seat_efficiency_dollar': _safe_float(row.get('Best Seat Efficiency/$')),
            'best_all_around_dollar': _safe_float(row.get('Best All Around/$')),
            'best_seat_all_around_dollar': _safe_float(row.get('Best Seat All Around/$')),
            'hourly_cost_per_seat': _safe_float(row.get('Hourly Cost/Seat')),
            'cost_per_mile': _safe_float(row.get('Cost/Mile')),
            'cost_per_seat_mile': _safe_float(row.get('Cost/Seat Mile')),
            'hourly_variable_cost': _safe_float(row.get('Hourly Variable Cost')),
            'variable_cost_per_seat': _safe_float(row.get('Variable Cost/Seat')),
            'variable_cost_per_mile': _safe_float(row.get('Variable Cost/Mile')),
            'variable_cost_per_seat_mile': _safe_float(row.get('Variable Cost/Seat Mile')),
            'BF': _safe_float(row.get('Best All Around/$')),
        }
        try:
            aircraft['performance_profile'] = _generate_performance_profile(aircraft)
        except ValueError:
            continue
        out.append(aircraft)
    return out


def load_airports_from_json(path):
    """Load airports from JSON, return list of dicts."""
    with open(path, 'r') as f:
        return json.load(f)
