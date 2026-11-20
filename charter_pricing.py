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
        'piston_single': 3.0,
        'piston_multi': 3.0,
        'turboprop_single': 2.75,
        'turboprop_multi': 2.75,
        'very_light': 2.5,
        'light': 2.5,
        'midsize': 2.4,
        'super_midsize': 2.25,
        'large': 2.1,
        'ultra_long': 2.0,
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

DISCLAIMER = 'The operator sets the final price.'

CATEGORY_ORDER = (
    'piston_single',
    'piston_multi',
    'turboprop_single',
    'turboprop_multi',
    'very_light',
    'light',
    'midsize',
    'super_midsize',
    'large',
    'ultra_long',
)

CATEGORY_LABELS = {
    'piston_single': 'Piston single',
    'piston_multi': 'Piston multi',
    'turboprop_single': 'Turboprop single',
    'turboprop_multi': 'Turboprop multi',
    'very_light': 'Very light jet',
    'light': 'Light jet',
    'midsize': 'Midsize jet',
    'super_midsize': 'Super midsize jet',
    'large': 'Large jet',
    'ultra_long': 'Ultra-long range jet',
}


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


def _multi_engine(aircraft: dict) -> bool | None:
    raw = aircraft.get('multi_engine')
    if isinstance(raw, bool):
        return raw
    text = str(raw or '').strip().lower()
    if text in ('yes', 'true', '1', 'y', 'multi'):
        return True
    if text in ('no', 'false', '0', 'n', 'single'):
        return False
    return None


def charter_category(aircraft: dict, override: str | None = None) -> str | None:
    """Planning class from engine type, then range. A missing range falls back to seats."""
    chosen = (override or '').strip().lower().replace('-', '_').replace(' ', '_')
    aliases = {
        'vlj': 'very_light',
        'very_light_jet': 'very_light',
        'light_jet': 'light',
        'midsize_jet': 'midsize',
        'super_midsize_jet': 'super_midsize',
        'large_jet': 'large',
        'large_cabin': 'large',
        'ultra_long_range': 'ultra_long',
        'ultra_long_range_jet': 'ultra_long',
        'ulr': 'ultra_long',
    }
    if chosen in DEFAULTS['multipliers']:
        return chosen
    if chosen in aliases:
        return aliases[chosen]
    kind = str(aircraft.get('category') or '').lower()
    if chosen == 'piston':
        kind = 'piston'
    elif chosen in ('turboprop', 'turbo_prop'):
        kind = 'turboprop'
    multi = _multi_engine(aircraft)
    if 'piston' in kind:
        return 'piston_multi' if multi else 'piston_single'
    if 'turboprop' in kind or 'turbo prop' in kind or 'turbo-prop' in kind:
        return 'turboprop_multi' if multi else 'turboprop_single'
    if 'jet' not in kind and 'business' not in kind:
        return None
    distance = _num(aircraft.get('range')) or 0
    passengers = _num(aircraft.get('passengers')) or 0
    if distance:
        if distance >= 5700 or (passengers >= 16 and distance >= 5500):
            return 'ultra_long'
        if distance >= 4500 or (passengers >= 12 and distance >= 3300):
            return 'large'
        if distance >= 2900:
            return 'super_midsize'
        if distance >= 2200:
            return 'midsize'
        if distance >= 1100:
            return 'light'
        return 'very_light'
    if passengers <= 6:
        return 'very_light'
    if passengers <= 8:
        return 'light'
    if passengers <= 9:
        return 'midsize'
    if passengers <= 12:
        return 'super_midsize'
    if passengers <= 16:
        return 'large'
    return 'ultra_long'


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
    """One customer price. The commission amount and the old range stay off this payload."""
    return {
        'pricing_status': result.get('status'),
        'charter_class': result.get('category'),
        'category_label': CATEGORY_LABELS.get(result.get('category') or '', ''),
        'hourly_charter_rate': result.get('hourly_rate'),
        'estimated_total': result.get('estimate_mid'),
        'price_note': result.get('price_note'),
    }
