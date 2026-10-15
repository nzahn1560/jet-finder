"""Charter estimates, mechanic shops, and broker locations.

Charter prices come from the aircraft already stored for Jet Finder. The
spreadsheet itself stays on the server; these helpers return a short estimate.
"""
from __future__ import annotations

import math
from typing import Any

import db as db_module

_AIRPORTS: list[dict] | None = None
_BY_CODE: dict[str, dict] | None = None
_BY_CITY: dict[str, list[dict]] | None = None

_SIZE_RANK = {'L': 0, 'M': 1, 'S': 2}
_US_STATES = {
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA',
    'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT',
    'VA', 'WA', 'WV', 'WI', 'WY', 'DC',
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
    """Match an airport code or city name to one airport."""
    raw = (text or '').strip()
    if len(raw) < 2:
        return None
    _load_indexes()
    assert _BY_CODE is not None and _BY_CITY is not None
    token = raw.split(',')[0].strip().upper()
    if token in _BY_CODE:
        return _BY_CODE[token]
    if token in _BY_CITY:
        return _prefer(_BY_CITY[token], country)
    contains = []
    for city, rows in _BY_CITY.items():
        if token in city or city in token:
            contains.extend(rows)
    return _prefer(contains, country)


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
