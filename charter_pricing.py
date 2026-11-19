"""Charter planning rates built from the aircraft spreadsheet.

Total Hourly Cost in the spreadsheet is fixed ownership cost plus variable cost,
spread over the sheet's annual hours. Hourly Charter Rate is half of Hourly
Variable Cost. That column is an ownership credit, not a market charter quote.

Estimates use Hourly Variable Cost and a category multiplier. A verified hourly
rate replaces the multiplier when an administrator has recorded one and dated it.
Missing costs stay missing.
"""
from __future__ import annotations

import copy
import math
from datetime import date, datetime
from typing import Any


DEFAULTS: dict[str, Any] = {
    'multipliers': {
        'piston': 3.0,
        'turboprop': 2.75,
        'very_light': 2.5,
        'light': 2.5,
        'midsize': 2.4,
        'super_midsize': 2.25,
        'large': 2.1,
    },
    'reposition_low': 0.10,
    'reposition_mid': 0.25,
    'reposition_high': 0.50,
    'airport_allowance': 500.0,
    'stop_handling_fee': 250.0,
    'minimum_billable_hours': None,
    'commission_rate': 0.10,
    'domestic_percentage_tax': 0.075,
    'domestic_segment_tax': 5.30,
    'international_head_tax': 23.40,
    'tax_year': 2026,
    'verified_rate_days': 540,
    'overrides': {},
}

DISCLAIMER = (
    'Estimated charter pricing is for planning purposes only. Actual availability, '
    'routing, operating requirements, repositioning expenses, and final pricing must '
    'be confirmed with an authorized charter operator.'
)


def merged(config: dict | None = None) -> dict:
    base = copy.deepcopy(DEFAULTS)
    for key, value in (config or {}).items():
        if key in ('multipliers', 'overrides') and isinstance(value, dict):
            base[key].update(value)
        elif key in base:
            base[key] = value
    return base


def active_config() -> dict:
    """Saved administrator settings, or the defaults when none have been saved."""
    try:
        import db as db_module
        saved = db_module.get_charter_pricing_config()
    except Exception:
        saved = None
    return merged(saved)


def _num(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number) or number <= 0:
        return None
    return number


def charter_category(aircraft: dict, override: str | None = None) -> str | None:
    """A planning class. Jet classes use the passengers and range already on the row."""
    chosen = (override or '').strip().lower().replace('-', '_').replace(' ', '_')
    if chosen in DEFAULTS['multipliers']:
        return chosen
    kind = str(aircraft.get('category') or '').lower()
    if 'piston' in kind:
        return 'piston'
    if 'turboprop' in kind or 'turbo prop' in kind:
        return 'turboprop'
    if 'jet' not in kind:
        return None
    passengers = _num(aircraft.get('passengers')) or 0
    distance = _num(aircraft.get('range')) or 0
    if not passengers or not distance:
        return None
    if passengers <= 6 and distance < 1800:
        return 'very_light'
    if passengers <= 8 and distance < 2500:
        return 'light'
    if passengers <= 9 and distance < 3500:
        return 'midsize'
    if passengers <= 12 and distance < 4500:
        return 'super_midsize'
    return 'large'


def _override(config: dict, aircraft: dict) -> dict:
    raw = (config.get('overrides') or {}).get(str(aircraft.get('id') or '')) or {}
    return raw if isinstance(raw, dict) else {}


def _verified_rate(override: dict, config: dict) -> float | None:
    rate = _num(override.get('verified_hourly_rate'))
    text = str(override.get('verified_on') or '').strip()
    if not rate or not text:
        return None
    try:
        verified = datetime.strptime(text[:10], '%Y-%m-%d').date()
    except ValueError:
        return None
    age = (date.today() - verified).days
    if age < 0 or age > int(config.get('verified_rate_days') or 540):
        return None
    return rate


def hourly_rate(aircraft: dict, config: dict | None = None) -> dict:
    """The planning hourly rate, or an unavailable result when the sheet has no variable cost."""
    settings = merged(config)
    override = _override(settings, aircraft)
    variable = _num(override.get('variable_hourly_cost')) or _num(aircraft.get('hourly_variable_cost'))
    verified = _verified_rate(override, settings)
    category = charter_category(aircraft, override.get('category'))
    multiplier = settings['multipliers'].get(category or '')
    if verified:
        return {
            'hourly_rate': verified,
            'variable_hourly_cost': variable,
            'category': category,
            'multiplier': None,
            'status': 'verified',
            'source': str(override.get('source') or '').strip(),
            'verified_on': str(override.get('verified_on') or '')[:10],
        }
    if not variable or not multiplier:
        return {
            'hourly_rate': None,
            'variable_hourly_cost': variable,
            'category': category,
            'multiplier': multiplier,
            'status': 'unavailable',
            'source': '',
            'verified_on': '',
        }
    return {
        'hourly_rate': variable * float(multiplier),
        'variable_hourly_cost': variable,
        'category': category,
        'multiplier': float(multiplier),
        'status': 'preliminary',
        'source': 'Hourly variable cost from the aircraft spreadsheet',
        'verified_on': '',
    }


def _round_hundred(value: float) -> int:
    return int(round(value / 100.0) * 100)


def price_mission(
    aircraft: dict,
    flight_hours: float | None,
    *,
    fuel_stops: int = 0,
    passengers: int = 1,
    round_trip: bool = False,
    domestic: bool = False,
    international: bool = False,
    config: dict | None = None,
) -> dict:
    """A low, middle, and high customer range. Commission stays out of the public fields."""
    settings = merged(config)
    rate = hourly_rate(aircraft, settings)
    empty = {
        'status': rate['status'],
        'category': rate['category'],
        'hourly_rate': rate['hourly_rate'],
        'estimate_low': None,
        'estimate_mid': None,
        'estimate_high': None,
        'tax_status': 'not_calculated',
        'price_note': 'A charter estimate is not available for this aircraft.',
    }
    hours = _num(flight_hours)
    if not rate['hourly_rate'] or not hours:
        return empty
    billable = hours
    minimum = _num(settings.get('minimum_billable_hours'))
    if minimum and billable < minimum:
        billable = minimum
    directions = 2 if round_trip else 1
    stops = max(0, int(fuel_stops or 0))
    fees = float(settings['airport_allowance']) * directions
    fees += float(settings['stop_handling_fee']) * stops * directions
    flight_charge = rate['hourly_rate'] * billable
    commission = float(settings['commission_rate'])
    if commission <= 0 or commission >= 1:
        commission = 0.10
    pax = max(1, int(passengers or 1))
    segments = (stops + 1) * directions

    def scenario(reposition_share: float) -> tuple[float, float]:
        operator = flight_charge + (flight_charge * reposition_share) + fees
        before_tax = operator / (1 - commission)
        tax = 0.0
        if domestic:
            tax = before_tax * float(settings['domestic_percentage_tax'])
            tax += pax * segments * float(settings['domestic_segment_tax'])
        elif international:
            tax = pax * directions * float(settings['international_head_tax'])
        return before_tax, before_tax + tax

    low_pre, low_total = scenario(float(settings['reposition_low']))
    mid_pre, mid_total = scenario(float(settings['reposition_mid']))
    high_pre, high_total = scenario(float(settings['reposition_high']))
    if domestic:
        shown = (low_total, mid_total, high_total)
        tax_status = 'us_domestic'
    elif international:
        shown = (low_total, mid_total, high_total)
        tax_status = 'international_head_tax'
    else:
        shown = (low_pre, mid_pre, high_pre)
        tax_status = 'not_calculated'
    low, mid, high = (_round_hundred(value) for value in shown)
    if high < low:
        low, high = high, low
    return {
        'status': rate['status'],
        'category': rate['category'],
        'hourly_rate': round(rate['hourly_rate'], 2),
        'billable_hours': round(billable, 2),
        'flight_charge': round(flight_charge, 2),
        'operator_mid': round(mid_pre * (1 - commission), 2),
        'before_tax_mid': round(mid_pre, 2),
        'commission_mid': round(mid_pre * commission, 2),
        'estimate_low': low,
        'estimate_mid': mid,
        'estimate_high': high,
        'tax_status': tax_status,
        'price_note': DISCLAIMER,
    }


def public_price(result: dict) -> dict:
    """Fields a visitor can see. The commission amount stays off this payload."""
    return {
        'pricing_status': result.get('status'),
        'hourly_charter_rate': result.get('hourly_rate'),
        'estimate_low': result.get('estimate_low'),
        'estimate_mid': result.get('estimate_mid'),
        'estimate_high': result.get('estimate_high'),
        'estimated_total': result.get('estimate_mid'),
        'tax_status': result.get('tax_status'),
        'price_note': result.get('price_note'),
    }
