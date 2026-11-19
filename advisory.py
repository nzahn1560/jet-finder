"""Free aircraft catalog and charter planning.

Prices and rates come from the aircraft spreadsheet already loaded for Jet Finder.
Missing numbers stay missing. This module does not invent charter rates, landing
distances, or airport fuel availability.
"""
from __future__ import annotations

import math
import os
import re
from typing import Any, Callable

ROUTE_FACTOR = 1.08
RANGE_RESERVE = 0.85
MAX_CROSS_TRACK_NM = 80.0
MAX_DIVERSION_FACTOR = 1.45
CHARTER_RATE_MULTIPLE = 3.25
CREW_HOURS = 1.7
IMAGE_ROLES = ('exterior', 'cabin', 'cockpit', 'cabin-extra')


def slug_for(aircraft: dict) -> str:
    name = str(aircraft.get('aircraft_name') or aircraft.get('model') or 'aircraft')
    base = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-') or 'aircraft'
    return f"{base}-{int(aircraft.get('id') or 0)}"


def find_aircraft(rows: list[dict], slug: str) -> dict | None:
    wanted = (slug or '').strip().lower()
    for row in rows:
        if slug_for(row) == wanted:
            return row
    return None


def _num(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def display_number(value: Any, digits: int = 0) -> str:
    number = _num(value)
    if number is None or number == 0:
        return 'Unavailable'
    if digits == 0:
        return f'{int(round(number)):,}'
    return f'{number:,.{digits}f}'


def catalog_card(aircraft: dict) -> dict:
    price = _num(aircraft.get('price'))
    charter = _num(aircraft.get('charter_rate'))
    return {
        'id': aircraft.get('id'),
        'slug': slug_for(aircraft),
        'name': aircraft.get('aircraft_name') or 'Aircraft',
        'manufacturer': aircraft.get('manufacturer') or '',
        'category': aircraft.get('category') or '',
        'years': aircraft.get('date_range') or aircraft.get('years_range') or '',
        'passengers': aircraft.get('passengers') or None,
        'range_nm': aircraft.get('range') or None,
        'speed_kts': aircraft.get('speed') or None,
        'price': int(price) if price else None,
        'price_label': f'${int(price):,}' if price else 'Unavailable',
        'charter_rate': charter if charter else None,
        'hourly_ownership_cost': _num(aircraft.get('total_hourly_cost')) or None,
        'hourly_label': f"${_num(aircraft.get('total_hourly_cost')):,.0f}" if _num(aircraft.get('total_hourly_cost')) else 'Unavailable',
        'images': image_slots(aircraft),
    }


def image_slots(aircraft: dict) -> list[dict]:
    """R2 object keys for this model. A missing file is reported, not replaced."""
    slug = slug_for(aircraft)
    public = (os.environ.get('R2_PUBLIC_BASE_URL') or '').rstrip('/')
    root = os.path.join(os.path.dirname(__file__), 'static', 'aircraft', slug)
    slots = []
    for role in IMAGE_ROLES:
        key = f'aircraft/{slug}/{role}.webp'
        local = os.path.join(root, f'{role}.webp')
        present = os.path.isfile(local)
        url = f'{public}/{key}' if public and present is False and public else ''
        if present:
            url = f'/static/aircraft/{slug}/{role}.webp'
        elif public:
            url = f'{public}/{key}'
        slots.append({
            'role': role,
            'key': key,
            'url': url,
            'present': present,
            'label': {
                'exterior': 'Exterior',
                'cabin': 'Passenger cabin',
                'cockpit': 'Cockpit',
                'cabin-extra': 'Additional cabin',
            }[role],
        })
    return slots


def missing_image_report(rows: list[dict]) -> list[dict]:
    missing = []
    for row in rows:
        absent = [slot['role'] for slot in image_slots(row) if not slot['present']]
        if absent:
            missing.append({'name': row.get('aircraft_name'), 'slug': slug_for(row), 'missing': absent})
    return missing


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 3440.065
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * radius * math.asin(min(1.0, math.sqrt(max(0.0, a))))


def _along_cross(origin: dict, dest: dict, point: dict, total: float) -> tuple[float, float]:
    ap = _haversine(origin['lat'], origin['lon'], point['lat'], point['lon'])
    bp = _haversine(dest['lat'], dest['lon'], point['lat'], point['lon'])
    if total <= 0:
        return 0.0, ap
    along = (total * total + ap * ap - bp * bp) / (2 * total)
    cross_sq = ap * ap - along * along
    return along, math.sqrt(cross_sq) if cross_sq > 0 else 0.0


def _code(airport: dict) -> str:
    return str(airport.get('iata') or airport.get('icao') or '').upper()


def _runway(airport: dict, runways: dict) -> int | None:
    for key in (airport.get('icao'), airport.get('iata'), _code(airport)):
        token = str(key or '').strip().upper()
        if token and token in runways:
            try:
                feet = int(runways[token])
            except (TypeError, ValueError):
                continue
            if feet > 0:
                return feet
    return None


def _point(airport: dict, runways: dict) -> dict:
    return {
        'code': _code(airport),
        'name': airport.get('name') or _code(airport),
        'lat': airport.get('lat'),
        'lon': airport.get('lon'),
        'runway_ft': _runway(airport, runways),
        'kind': 'airport',
    }


def _leg(a: dict, b: dict) -> dict:
    distance = _haversine(a['lat'], a['lon'], b['lat'], b['lon']) * ROUTE_FACTOR
    return {'from': a['code'], 'to': b['code'], 'nm': round(distance, 1)}


def _usable_range(aircraft: dict) -> float | None:
    published = _num(aircraft.get('range'))
    if not published or published <= 0:
        return None
    return published * RANGE_RESERVE


def _candidates(origin: dict, dest: dict, airports: list[dict], runways: dict, total: float) -> list[dict]:
    found = []
    seen = set()
    for airport in airports:
        lat, lon = airport.get('lat'), airport.get('lon')
        if lat is None or lon is None:
            continue
        code = _code(airport)
        if not code or code in seen or code in {origin['code'], dest['code']}:
            continue
        along, cross = _along_cross(origin, dest, airport, total)
        if along < total * 0.12 or along > total * 0.88 or cross > MAX_CROSS_TRACK_NM:
            continue
        runway = _runway(airport, runways)
        if not runway:
            continue
        seen.add(code)
        found.append({
            'code': code,
            'name': airport.get('name') or code,
            'lat': lat,
            'lon': lon,
            'runway_ft': runway,
            'along': along,
            'kind': 'fuel_stop',
            'fuel_verified': False,
        })
    found.sort(key=lambda row: row['along'])
    return found


def _takeoff_fits(runway_ft: int | None, field_length: float | None) -> bool | None:
    """True, False, or None when the runway length is unknown."""
    if not field_length or field_length <= 0:
        return None
    if not runway_ft:
        return None
    return runway_ft >= field_length


def _charter_rate(aircraft: dict) -> float | None:
    """Charter rate is 325% of the spreadsheet total hourly operating cost."""
    hourly = _num(aircraft.get('total_hourly_cost'))
    if not hourly or hourly <= 0:
        return None
    return hourly * CHARTER_RATE_MULTIPLE


def _hours(distance_nm: float, speed: float, legs: int) -> float | None:
    if speed <= 0:
        return None
    return distance_nm / speed + (0.3 * legs)


def plan_charter(
    origin: dict,
    destination: dict,
    aircraft_list: list[dict],
    airports: list[dict],
    runways: dict,
    passengers: int = 1,
    round_trip: bool = False,
) -> dict:
    """Compare aircraft for one mission.

    Runway fit uses the same rule as Jet Finder: balanced field length must be
    no longer than the recorded runway at every airport on the route. The
    charter price is 325% of total hourly operating cost, plus 1.7 crew hours.
    """
    start = _point(origin, runways)
    end = _point(destination, runways)
    if start['lat'] is None or end['lat'] is None:
        return {'ok': False, 'error': 'Both airports need coordinates.'}
    if start['code'] and start['code'] == end['code']:
        return {'ok': False, 'error': 'Choose two different airports.'}
    direct = _haversine(start['lat'], start['lon'], end['lat'], end['lon'])
    trip_nm = direct * ROUTE_FACTOR
    stops_pool = _candidates(start, end, airports, runways, direct) if trip_nm > 0 else []
    pax = max(1, int(passengers or 1))
    suitable = []
    unverified = []
    excluded = {'seats': 0, 'range': 0, 'runway': 0, 'stops': 0, 'missing': 0}

    for aircraft in aircraft_list:
        name = aircraft.get('aircraft_name') or aircraft.get('model') or 'Aircraft'
        seats = int(_num(aircraft.get('passengers')) or 0)
        speed = _num(aircraft.get('speed')) or 0
        field = _num(aircraft.get('runway_length'))
        usable = _usable_range(aircraft)
        if seats < pax:
            excluded['seats'] += 1
            continue
        if not usable or speed <= 0:
            excluded['missing'] += 1
            continue
        route = _route_for(start, end, trip_nm, usable, stops_pool, field)
        if route is None:
            excluded['stops'] += 1
            continue
        takeoff_checks = [_takeoff_fits(point.get('runway_ft'), field) for point in route['points']]
        if any(item is False for item in takeoff_checks):
            excluded['runway'] += 1
            continue
        takeoff_ok = bool(field) and all(item is True for item in takeoff_checks)
        confirmed = takeoff_ok
        if takeoff_ok:
            runway_status = 'Balanced field length fits the longest runway at each airport on this route'
        elif not field:
            runway_status = 'A runway requirement is not available for this aircraft'
        else:
            runway_status = 'Runway length is not recorded for every airport on this route'
        rate = _charter_rate(aircraft)
        one_way_nm = route['distance_nm']
        hours = _hours(one_way_nm * (2 if round_trip else 1), speed, route['legs'] * (2 if round_trip else 1))
        billed = round(hours + CREW_HOURS, 2) if hours else None
        estimate = int(round(billed * rate)) if billed and rate else None
        card = {
            'id': aircraft.get('id'),
            'slug': slug_for(aircraft),
            'name': name,
            'manufacturer': aircraft.get('manufacturer') or '',
            'category': aircraft.get('category') or '',
            'passengers': seats,
            'range_nm': int(_num(aircraft.get('range')) or 0),
            'speed_kts': int(speed),
            'cabin_volume': _num(aircraft.get('cabin_volume')),
            'fuel_stops': route['stops'],
            'stop_label': _stop_label(route['stops']),
            'runway_length': int(field) if field else None,
            'max_altitude': int(_num(aircraft.get('max_altitude')) or 0) or None,
            'wingspan': _num(aircraft.get('wingspan')),
            'flight_hours': round(hours, 2) if hours else None,
            'crew_hours': CREW_HOURS,
            'billed_hours': billed,
            'distance_nm': round(one_way_nm * (2 if round_trip else 1), 1),
            'hourly_operating_cost': _num(aircraft.get('total_hourly_cost')) or None,
            'hourly_charter_rate': round(rate, 2) if rate else None,
            'estimated_total': estimate,
            'price_note': (
                'This estimate includes flight time and crew. It is not a confirmed quote. '
                'An authorized operator confirms the final figure.'
                if estimate else
                'A charter estimate is not available for this aircraft.'
            ),
            'confirmed_suitable': confirmed,
            'runway_status': runway_status,
            'fuel_status': 'Nonstop' if route['stops'] == 0 else 'Fuel stop calculated from range',
            'points': route['points'],
            'legs': route['legs_detail'],
        }
        if confirmed:
            suitable.append(card)
        else:
            unverified.append(card)

    unverified.sort(key=lambda row: (row['fuel_stops'], row['estimated_total'] or 10 ** 12, row['name']))
    return {
        'ok': True,
        'passengers': pax,
        'round_trip': bool(round_trip),
        'distance_nm': round(trip_nm, 1),
        'origin': start,
        'destination': end,
        'suitable': suitable,
        'unverified': unverified,
        'excluded': excluded,
        'notice': (
            'Aircraft are compared for this charter the same way they are compared for a purchase. '
            'A result is shown when the aircraft can fly the mission and its runway requirement fits '
            'the airports. The price is a charter estimate. An authorized operator confirms the '
            'aircraft and the final figure. Jetschool is not the operator.'
        ),
    }


def _stop_label(stops: int) -> str:
    if stops <= 0:
        return 'Nonstop'
    if stops == 1:
        return '1 Fuel Stop Required'
    return '2 Fuel Stops Required'


def _route_for(start, end, trip_nm, usable, pool, field) -> dict | None:
    if trip_nm <= usable:
        return {
            'stops': 0,
            'distance_nm': trip_nm,
            'points': [start, end],
            'legs': 1,
            'legs_detail': [_leg(start, end)],
            'fuel_verified': True,
        }
    usable_pool = [point for point in pool if not field or _takeoff_fits(point.get('runway_ft'), field) is True]
    one = _one_stop(start, end, usable, usable_pool)
    if one:
        return one
    two = _two_stops(start, end, usable, usable_pool, trip_nm)
    return two


def _one_stop(start, end, usable, pool) -> dict | None:
    best = None
    for stop in pool:
        first = _haversine(start['lat'], start['lon'], stop['lat'], stop['lon']) * ROUTE_FACTOR
        second = _haversine(stop['lat'], stop['lon'], end['lat'], end['lon']) * ROUTE_FACTOR
        if first > usable or second > usable:
            continue
        total = first + second
        if best is None or total < best['distance_nm']:
            best = {
                'stops': 1,
                'distance_nm': total,
                'points': [start, stop, end],
                'legs': 2,
                'legs_detail': [_leg(start, stop), _leg(stop, end)],
                'fuel_verified': False,
            }
    return best


def _two_stops(start, end, usable, pool, direct_nm) -> dict | None:
    best = None
    limited = pool[:40]
    for i, first in enumerate(limited):
        for second in limited[i + 1:]:
            legs = [
                _haversine(start['lat'], start['lon'], first['lat'], first['lon']) * ROUTE_FACTOR,
                _haversine(first['lat'], first['lon'], second['lat'], second['lon']) * ROUTE_FACTOR,
                _haversine(second['lat'], second['lon'], end['lat'], end['lon']) * ROUTE_FACTOR,
            ]
            if any(leg > usable for leg in legs):
                continue
            total = sum(legs)
            if direct_nm and total > direct_nm * MAX_DIVERSION_FACTOR:
                continue
            if best is None or total < best['distance_nm']:
                best = {
                    'stops': 2,
                    'distance_nm': total,
                    'points': [start, first, second, end],
                    'legs': 3,
                    'legs_detail': [_leg(start, first), _leg(first, second), _leg(second, end)],
                    'fuel_verified': False,
                }
    return best
