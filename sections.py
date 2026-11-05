"""Charter estimates, mechanic shops, and broker locations.

Charter prices come from the aircraft already stored for Jet Finder. The
spreadsheet itself stays on the server; these helpers return a short estimate.
"""
from __future__ import annotations

import json
import math
import os
import re
from typing import Any

import db as db_module

_AIRPORTS: list[dict] | None = None
_BY_CODE: dict[str, dict] | None = None
_BY_CITY: dict[str, list[dict]] | None = None
_PLACES: dict[str, list] | None = None

_SIZE_RANK = {'L': 0, 'M': 1, 'S': 2}
_US_STATES = {
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA',
    'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT',
    'VA', 'WA', 'WV', 'WI', 'WY', 'DC',
}
_STATE_NAMES = {
    'ALABAMA': 'AL', 'ALASKA': 'AK', 'ARIZONA': 'AZ', 'ARKANSAS': 'AR', 'CALIFORNIA': 'CA',
    'COLORADO': 'CO', 'CONNECTICUT': 'CT', 'DELAWARE': 'DE', 'FLORIDA': 'FL', 'GEORGIA': 'GA',
    'HAWAII': 'HI', 'IDAHO': 'ID', 'ILLINOIS': 'IL', 'INDIANA': 'IN', 'IOWA': 'IA',
    'KANSAS': 'KS', 'KENTUCKY': 'KY', 'LOUISIANA': 'LA', 'MAINE': 'ME', 'MARYLAND': 'MD',
    'MASSACHUSETTS': 'MA', 'MICHIGAN': 'MI', 'MINNESOTA': 'MN', 'MISSISSIPPI': 'MS',
    'MISSOURI': 'MO', 'MONTANA': 'MT', 'NEBRASKA': 'NE', 'NEVADA': 'NV', 'NEW HAMPSHIRE': 'NH',
    'NEW JERSEY': 'NJ', 'NEW MEXICO': 'NM', 'NEW YORK': 'NY', 'NORTH CAROLINA': 'NC',
    'NORTH DAKOTA': 'ND', 'OHIO': 'OH', 'OKLAHOMA': 'OK', 'OREGON': 'OR', 'PENNSYLVANIA': 'PA',
    'RHODE ISLAND': 'RI', 'SOUTH CAROLINA': 'SC', 'SOUTH DAKOTA': 'SD', 'TENNESSEE': 'TN',
    'TEXAS': 'TX', 'UTAH': 'UT', 'VERMONT': 'VT', 'VIRGINIA': 'VA', 'WASHINGTON': 'WA',
    'WEST VIRGINIA': 'WV', 'WISCONSIN': 'WI', 'WYOMING': 'WY', 'DISTRICT OF COLUMBIA': 'DC',
}
# Inclusive boxes. These keep a named state from accepting an airport on another continent.
_STATE_BOXES = {
    'AL': (30.1, 35.1, -88.6, -84.8), 'AK': (51.0, 71.6, -179.5, -129.0),
    'AZ': (31.3, 37.1, -114.9, -109.0), 'AR': (33.0, 36.6, -94.7, -89.6),
    'CA': (32.5, 42.1, -124.5, -114.1), 'CO': (36.9, 41.1, -109.1, -102.0),
    'CT': (40.9, 42.1, -73.8, -71.7), 'DE': (38.4, 39.9, -75.8, -74.8),
    'FL': (24.4, 31.1, -87.7, -80.0), 'GA': (30.3, 35.1, -85.7, -80.7),
    'HI': (18.8, 22.3, -160.3, -154.7), 'ID': (41.9, 49.1, -117.3, -111.0),
    'IL': (36.9, 42.6, -91.6, -87.0), 'IN': (37.7, 41.8, -88.1, -84.7),
    'IA': (40.3, 43.6, -96.7, -90.1), 'KS': (36.9, 40.1, -102.1, -94.6),
    'KY': (36.5, 39.2, -89.6, -81.9), 'LA': (28.9, 33.1, -94.1, -88.8),
    'ME': (43.0, 47.5, -71.1, -66.9), 'MD': (37.9, 39.8, -79.5, -75.0),
    'MA': (41.2, 42.9, -73.6, -69.9), 'MI': (41.7, 48.3, -90.5, -82.4),
    'MN': (43.4, 49.4, -97.3, -89.5), 'MS': (30.1, 35.1, -91.7, -88.1),
    'MO': (35.9, 40.7, -95.8, -89.1), 'MT': (44.3, 49.1, -116.1, -104.0),
    'NE': (39.9, 43.1, -104.1, -95.3), 'NV': (35.0, 42.1, -120.1, -114.0),
    'NH': (42.7, 45.4, -72.6, -70.6), 'NJ': (38.9, 41.4, -75.6, -73.9),
    'NM': (31.3, 37.1, -109.1, -103.0), 'NY': (40.5, 45.1, -79.8, -71.8),
    'NC': (33.8, 36.6, -84.4, -75.4), 'ND': (45.9, 49.1, -104.1, -96.5),
    'OH': (38.4, 42.0, -84.9, -80.5), 'OK': (33.6, 37.1, -103.1, -94.4),
    'OR': (41.9, 46.3, -124.6, -116.4), 'PA': (39.7, 42.3, -80.6, -74.7),
    'RI': (41.1, 42.1, -71.9, -71.1), 'SC': (32.0, 35.3, -83.4, -78.5),
    'SD': (42.5, 46.0, -104.1, -96.4), 'TN': (34.9, 36.7, -90.4, -81.6),
    'TX': (25.8, 36.6, -106.7, -93.5), 'UT': (36.9, 42.1, -114.1, -109.0),
    'VT': (42.7, 45.1, -73.5, -71.5), 'VA': (36.5, 39.5, -83.7, -75.2),
    'WA': (45.5, 49.1, -124.8, -116.9), 'WV': (37.2, 40.7, -82.7, -77.7),
    'WI': (42.5, 47.1, -92.9, -86.8), 'WY': (40.9, 45.1, -111.1, -104.0),
    'DC': (38.79, 39.0, -77.12, -76.9),
}
_COUNTRY_NAMES = {
    'FRANCE': 'FR', 'CANADA': 'CA', 'MEXICO': 'MX', 'UNITED KINGDOM': 'GB', 'UK': 'GB',
    'GERMANY': 'DE', 'AUSTRALIA': 'AU', 'BRAZIL': 'BR', 'JAPAN': 'JP', 'INDIA': 'IN',
    'ITALY': 'IT', 'SPAIN': 'ES', 'CHINA': 'CN', 'CONGO': 'CG', 'SOUTH AFRICA': 'ZA',
}


def normalize_market(value: Any) -> str:
    raw = str(value or '').strip().lower().replace('-', '_')
    if raw in ('off_market', 'broker_only'):
        return 'broker_only'
    if raw == 'private':
        return 'private'
    return 'public'


def _load_indexes() -> None:
    global _AIRPORTS, _BY_CODE, _BY_CITY
    if _AIRPORTS is not None:
        return
    airports = db_module.get_all_airports()
    by_code: dict[str, dict] = {}
    by_city: dict[str, list[dict]] = {}
    for airport in airports:
        for key in ('iata', 'icao'):
            code = (airport.get(key) or '').strip().upper()
            if code and code not in by_code:
                by_code[code] = airport
        city = (airport.get('city') or '').strip().upper()
        if city:
            by_city.setdefault(city, []).append(airport)
    _AIRPORTS = airports
    _BY_CODE = by_code
    _BY_CITY = by_city


def _load_places() -> None:
    global _PLACES
    if _PLACES is not None:
        return
    path = os.path.join(os.path.dirname(__file__), 'static', 'data', 'us_places.json')
    try:
        with open(path, encoding='utf-8') as handle:
            _PLACES = json.load(handle)
    except OSError:
        _PLACES = {}


def _norm_name(value: str) -> str:
    return ' '.join(re.sub(r'[^A-Z0-9 ]+', ' ', (value or '').upper()).split())


def _region_code(text: str) -> str | None:
    token = _norm_name(text)
    if token in _US_STATES:
        return token
    return _STATE_NAMES.get(token)


def _country_code(text: str) -> str | None:
    return _COUNTRY_NAMES.get(_norm_name(text))


def _split_place(text: str) -> tuple[str, str | None, str | None]:
    """City, US state, and a country named in the text."""
    cleaned = ' '.join((text or '').strip().split())
    if not cleaned:
        return '', None, None
    if ',' in cleaned:
        city, rest = cleaned.split(',', 1)
        region = _region_code(rest)
        if region:
            return _norm_name(city), region, 'US'
        return _norm_name(city), None, _country_code(rest)
    parts = cleaned.split(' ')
    for size in (3, 2, 1):
        if len(parts) <= size:
            continue
        region = _region_code(' '.join(parts[-size:]))
        city = ' '.join(parts[:-size]).strip()
        if region and city:
            return _norm_name(city), region, 'US'
    return _norm_name(cleaned), None, None


def _in_state(lat: Any, lon: Any, region: str | None) -> bool:
    box = _STATE_BOXES.get(region or '')
    if not box:
        return True
    try:
        lat_n, lon_n = float(lat), float(lon)
    except (TypeError, ValueError):
        return False
    south, north, west, east = box
    return south <= lat_n <= north and west <= lon_n <= east


def _city_place(city: str, region: str | None) -> dict | None:
    """Coordinates for a US city. Rows are stored with the largest city first."""
    _load_places()
    assert _PLACES is not None
    rows = _PLACES.get(city) or []
    if region:
        rows = [row for row in rows if row[0] == region]
    if not rows:
        return None
    state, lat, lon = rows[0]
    label = city.title()
    return {
        'iata': '',
        'icao': '',
        'name': f'{label}, {state}',
        'city': label,
        'country': 'US',
        'lat': lat,
        'lon': lon,
        'size': '',
    }


def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in nautical miles."""
    radius = 3440.065
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * radius * math.asin(min(1.0, math.sqrt(a)))


def _prefer(matches: list[dict], country: str | None) -> dict | None:
    if not matches:
        return None

    def rank(airport: dict) -> tuple:
        code = (airport.get('country') or '').upper()
        country_penalty = 0 if not country or code == country else 1
        size = _SIZE_RANK.get((airport.get('size') or 'S').upper(), 3)
        return (country_penalty, size, airport.get('name') or '')

    return sorted(matches, key=rank)[0]


def resolve_place(text: str | None, country: str | None = None) -> dict | None:
    """Match an airport code or a city and state to one point on the map."""
    raw = (text or '').strip()
    if len(raw) < 2:
        return None
    _load_indexes()
    assert _BY_CODE is not None and _BY_CITY is not None
    city, region, named_country = _split_place(raw)
    if not city:
        return None
    compact = _norm_name(raw).replace(' ', '')
    if region is None and named_country is None and ' ' not in raw and ',' not in raw and compact in _BY_CODE:
        return _BY_CODE[compact]
    if named_country in (None, 'US'):
        placed = _city_place(city, region)
        if placed:
            return placed
    matches = list(_BY_CITY.get(city) or [])
    if region:
        matches = [airport for airport in matches if _in_state(airport.get('lat'), airport.get('lon'), region)]
    wanted = named_country or ('US' if region else country)
    if wanted:
        home = [airport for airport in matches if (airport.get('country') or '').upper() == wanted]
        if home:
            matches = home
    return _prefer(matches, wanted)


def _hourly_rate(aircraft: dict) -> float:
    try:
        cost = float(aircraft.get('total_hourly_cost') or 0)
    except (TypeError, ValueError):
        cost = 0
    if cost > 0:
        return cost
    category = (aircraft.get('category') or '').lower()
    if 'piston' in category or 'turbo' in category:
        return 2200.0
    if 'heavy' in category or 'ultra' in category or 'long' in category:
        return 8500.0
    if 'mid' in category:
        return 4500.0
    return 3200.0


def _number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def estimate_charter(departure: str, arrival: str, passengers: int, aircraft_list: list[dict]) -> dict:
    """Rank aircraft that can fly the route. Returns an estimate, not a live quote."""
    origin = resolve_place(departure)
    destination = resolve_place(arrival)
    if not origin or not destination:
        missing = []
        if not origin:
            missing.append('departure airport')
        if not destination:
            missing.append('arrival airport')
        return {'ok': False, 'error': 'Could not find the ' + ' or '.join(missing) + '.'}
    if (origin.get('iata') or origin.get('icao')) == (destination.get('iata') or destination.get('icao')) and (
        origin.get('lat') == destination.get('lat') and origin.get('lon') == destination.get('lon')
    ):
        return {'ok': False, 'error': 'Choose two different airports.'}

    distance = haversine_nm(origin['lat'], origin['lon'], destination['lat'], destination['lon'])
    # Airways run longer than the great-circle line.
    trip_nm = distance * 1.08
    pax = max(1, int(passengers or 1))
    options = []
    for aircraft in aircraft_list:
        aircraft_range = _number(aircraft.get('range'))
        speed = _number(aircraft.get('speed'))
        seats = int(_number(aircraft.get('passengers')))
        if aircraft_range < trip_nm or speed < 80 or seats < pax:
            continue
        hours = trip_nm / speed + 0.4
        rate = _hourly_rate(aircraft)
        name = aircraft.get('aircraft_name') or aircraft.get('name') or 'Aircraft'
        options.append({
            'name': name,
            'manufacturer': aircraft.get('manufacturer') or '',
            'category': aircraft.get('category') or '',
            'passengers': seats,
            'range_nm': int(aircraft_range),
            'speed_kts': int(speed),
            'flight_hours': round(hours, 1),
            'hourly_rate': int(round(rate)),
            'estimated_total': int(round(hours * rate)),
        })
    options.sort(key=lambda row: row['estimated_total'])
    return {
        'ok': True,
        'departure': _airport_brief(origin),
        'arrival': _airport_brief(destination),
        'distance_nm': int(round(trip_nm)),
        'passengers': pax,
        'aircraft': options[:8],
        'note': 'Estimate from JetSchool performance data. It is not a confirmed charter quote.',
    }


def _airport_brief(airport: dict) -> dict:
    code = airport.get('iata') or airport.get('icao') or ''
    return {
        'code': code,
        'name': airport.get('name') or code,
        'city': airport.get('city') or '',
        'lat': airport.get('lat'),
        'lon': airport.get('lon'),
    }


def place_on_map(people: list[dict], location_key: str = 'profile_location') -> list[dict]:
    """Attach lat/lon when a location string matches an airport. Offset stacked pins."""
    placed = []
    seen: dict[tuple, int] = {}
    for person in people:
        row = dict(person)
        airport = resolve_place(row.get(location_key), country='US')
        if airport and airport.get('lat') is not None and airport.get('lon') is not None:
            key = (round(float(airport['lat']), 3), round(float(airport['lon']), 3))
            slot = seen.get(key, 0)
            seen[key] = slot + 1
            angle = slot * 0.9
            row['lat'] = float(airport['lat']) + math.sin(angle) * 0.08 * slot
            row['lon'] = float(airport['lon']) + math.cos(angle) * 0.08 * slot
            row['airport_code'] = airport.get('iata') or airport.get('icao') or ''
            row['airport_name'] = airport.get('name') or ''
            row['airport_city'] = airport.get('city') or ''
        placed.append(row)
    return placed


def us_country_hint(state: str | None) -> str | None:
    token = (state or '').strip().upper()
    if token in _US_STATES or token in {'USA', 'US', 'UNITED STATES'}:
        return 'US'
    return None
