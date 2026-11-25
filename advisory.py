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
        'country': str(airport.get('country') or '').strip().upper(),
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
    """Planning charter rate from variable cost. Total hourly cost includes fixed ownership costs."""
    import charter_pricing
    return charter_pricing.hourly_rate(aircraft, charter_pricing.active_config()).get('hourly_rate')


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

    Runway fit uses the same rule as Jet Finder. The charter price is one planning figure.
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
    import charter_pricing
    pricing = charter_pricing.active_config()
    domestic = start.get('country') in ('US', 'USA') and end.get('country') in ('US', 'USA')
    international = not domestic and ('US' in (start.get('country'), end.get('country')) or 'USA' in (start.get('country'), end.get('country')))
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
        one_way_nm = route['distance_nm']
        hours = (direct / speed) if speed else None
        priced = charter_pricing.price_mission(
            aircraft,
            hours,
            fuel_stops=route['stops'],
            passengers=pax,
            round_trip=round_trip,
            domestic=domestic,
            international=international,
            config=pricing,
        )
        hours = priced.get('billable_hours') or hours
        public = charter_pricing.public_price(priced)
        photo = next((slot.get('url') for slot in image_slots(aircraft) if slot.get('present') and slot.get('url')), '')
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
            'cabin_height': _num(aircraft.get('cabin_height')),
            'cabin_width': _num(aircraft.get('cabin_width')),
            'cabin_length': _num(aircraft.get('cabin_length')),
            'fuel_stops': route['stops'],
            'stop_label': _stop_label(route['stops']),
            'runway_length': int(field) if field else None,
            'max_altitude': int(_num(aircraft.get('max_altitude')) or 0) or None,
            'wingspan': _num(aircraft.get('wingspan')),
            'flight_hours': round(hours, 2) if hours else None,
            'billed_hours': round(hours, 2) if hours else None,
            'distance_nm': round(one_way_nm * (2 if round_trip else 1), 1),
            'hourly_operating_cost': _num(aircraft.get('hourly_variable_cost')) or None,
            'image': photo,
            **public,
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

    _score_mission(suitable + unverified, pax)
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
        'categories': _best_by_category(suitable + unverified),
        'excluded': excluded,
        'notice': charter_pricing.DISCLAIMER,
    }


def _score_mission(cards: list[dict], passengers: int) -> None:
    """Best value for this trip: fill the seats asked for, then speed and the trip price.

    A higher percent is better. Seat use is the party size divided by the cabin.
    Speed and price are scaled across the airplanes that can fly this trip.
    """
    priced = [
        card for card in cards
        if card.get('estimated_total') and card.get('speed_kts') and (card.get('passengers') or 0) >= passengers
    ]
    speeds = [card['speed_kts'] for card in priced]
    prices = [card['estimated_total'] for card in priced]
    slow = min(speeds) if speeds else 0
    fast = max(speeds) if speeds else 0
    cheap = min(prices) if prices else 0
    dear = max(prices) if prices else 0
    for card in cards:
        seats = card.get('passengers') or 0
        speed = card.get('speed_kts') or 0
        price = card.get('estimated_total')
        if not price or not speed or seats < passengers:
            card['all_around_percent'] = None
            continue
        seat_use = passengers / seats
        speed_score = 1.0 if fast <= slow else (speed - slow) / (fast - slow)
        price_score = 1.0 if dear <= cheap else (dear - price) / (dear - cheap)
        card['all_around_percent'] = int(round((seat_use + speed_score + price_score) / 3 * 100))


def _best_by_category(cards: list[dict]) -> list[dict]:
    """One aircraft per class: the best value for this trip, then the lower price."""
    import charter_pricing
    groups: dict[str, list[dict]] = {}
    for card in cards:
        key = card.get('charter_class') or ''
        if key not in charter_pricing.CATEGORY_LABELS:
            continue
        groups.setdefault(key, []).append(card)
    picked = []
    for key in charter_pricing.CATEGORY_ORDER:
        rows = groups.get(key) or []
        if not rows:
            continue
        rows.sort(key=lambda row: (
            -(row.get('all_around_percent') if row.get('all_around_percent') is not None else -1),
            0 if row.get('confirmed_suitable') else 1,
            row.get('estimated_total') or 10 ** 12,
            row.get('name') or '',
        ))
        best = dict(rows[0])
        best['best_available'] = True
        best['category_label'] = charter_pricing.CATEGORY_LABELS[key]
        picked.append(best)
    return picked


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
