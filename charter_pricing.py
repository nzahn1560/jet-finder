"""Charter planning rates built from the aircraft spreadsheet.

The customer price is the spreadsheet Hourly Variable Cost, times the class
factor, times the flight hours. Flight hours are the great-circle distance
divided by the spreadsheet speed. A dated verified rate replaces that hourly
figure. Missing variable cost stays missing.
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
        'turboprop_multi': 1.85,
        'very_light': 2.35,
        'light': 2.04,
        'super_light': 1.86,
        'midsize': 2.54,
        'super_midsize': 2.22,
        'large': 2.56,
        'ultra_long': 2.07,
    },
    'reposition_low': 0.10,
    'reposition_mid': 0.25,
    'reposition_high': 0.50,
    'airport_allowance': 500.0,
    'stop_handling_fee': 250.0,
    'minimum_billable_hours': None,
    'commission_rate': 0.0,
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
    'super_light',
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
    'super_light': 'Super light jet',
    'midsize': 'Midsize jet',
    'super_midsize': 'Super midsize jet',
    'large': 'Heavy jet',
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


# Longest name first, so Citation XLS is not read as a Citation X and Falcon 2000 is not a Falcon 20.
# These are the classes US charter fleets publish for that airplane, not a cut on its spreadsheet range.
_JET_FAMILIES: tuple[tuple[str, str], ...] = tuple(sorted((
    ('GLOBAL 7500', 'ultra_long'),
    ('GLOBAL 6500', 'ultra_long'),
    ('GLOBAL 6000', 'ultra_long'),
    ('GLOBAL EXPRESS', 'ultra_long'),
    ('GLOBAL 5000', 'ultra_long'),
    ('FALCON 8X', 'ultra_long'),
    ('FALCON 7X', 'ultra_long'),
    ('G650ER', 'ultra_long'),
    ('G650', 'ultra_long'),
    ('G700', 'ultra_long'),
    ('G600', 'ultra_long'),
    ('G550', 'ultra_long'),
    ('G500', 'ultra_long'),
    ('G-V', 'ultra_long'),
    ('BBJ', 'ultra_long'),
    ('ACJ', 'ultra_long'),
    ('CHALLENGER 850', 'large'),
    ('CHALLENGER 650', 'large'),
    ('CHALLENGER 605', 'large'),
    ('CHALLENGER 604', 'large'),
    ('CHALLENGER 601', 'large'),
    ('FALCON 900', 'large'),
    ('LEGACY 650', 'large'),
    ('LEGACY 600', 'large'),
    ('LINEAGE', 'large'),
    ('G450', 'large'),
    ('G400', 'large'),
    ('G350', 'large'),
    ('G300', 'large'),
    ('G-IV', 'large'),
    ('G-III', 'large'),
    ('ERJ-145', 'large'),
    ('CHALLENGER 3500', 'super_midsize'),
    ('CHALLENGER 350', 'super_midsize'),
    ('CHALLENGER 300', 'super_midsize'),
    ('FALCON 2000', 'super_midsize'),
    ('FALCON 50', 'super_midsize'),
    ('PRAETOR 600', 'super_midsize'),
    ('LEGACY 500', 'super_midsize'),
    ('CITATION LONGITUDE', 'super_midsize'),
    ('CITATION X+', 'super_midsize'),
    ('CITATION X', 'super_midsize'),
    ('G280', 'super_midsize'),
    ('G200', 'super_midsize'),
    ('HAWKER 4000', 'super_midsize'),
    ('CITATION SOVEREIGN', 'midsize'),
    ('CITATION LATITUDE', 'midsize'),
    ('CITATION VII', 'midsize'),
    ('CITATION VI', 'midsize'),
    ('CITATION III', 'midsize'),
    ('PRAETOR 500', 'midsize'),
    ('LEGACY 450', 'midsize'),
    ('LEARJET 60', 'midsize'),
    ('LEARJET 55', 'midsize'),
    ('HAWKER 1000', 'midsize'),
    ('HAWKER 900', 'midsize'),
    ('HAWKER 850', 'midsize'),
    ('HAWKER 800', 'midsize'),
    ('HAWKER 750', 'midsize'),
    ('G150', 'midsize'),
    ('G100', 'midsize'),
    ('FALCON 20', 'midsize'),
    ('CITATION XLS', 'super_light'),
    ('CITATION EXCEL', 'super_light'),
    ('PC-24', 'super_light'),
    ('PHENOM 300', 'light'),
    ('LEARJET 75', 'light'),
    ('LEARJET 70', 'light'),
    ('LEARJET 45', 'light'),
    ('LEARJET 40', 'light'),
    ('LEARJET 36', 'light'),
    ('LEARJET 35', 'light'),
    ('LEARJET 31', 'light'),
    ('CITATION CJ4', 'light'),
    ('CITATION CJ3', 'light'),
    ('CITATION CJ2', 'light'),
    ('CITATION CJ1', 'light'),
    ('CITATION ENCORE', 'light'),
    ('CITATION BRAVO', 'light'),
    ('CITATION V', 'light'),
    ('CITATION SII', 'light'),
    ('CITATION II', 'light'),
    ('CITATION 500', 'light'),
    ('BEECHJET', 'light'),
    ('HAWKER 400', 'light'),
    ('NEXTANT', 'light'),
    ('PREMIER', 'light'),
    ('WESTWIND', 'light'),
    ('FALCON 10', 'light'),
    ('CITATION M2', 'very_light'),
    ('CITATION MUSTANG', 'very_light'),
    ('CITATION JET', 'very_light'),
    ('PHENOM 100', 'very_light'),
    ('HONDAJET', 'very_light'),
    ('ECLIPSE', 'very_light'),
    ('VISION', 'very_light'),
), key=lambda item: len(item[0]), reverse=True))


def _jet_family(name: str) -> str | None:
    text = str(name or '').strip().upper()
    if text in ('SP', 'SPX'):
        return 'midsize'
    for needle, category in _JET_FAMILIES:
        if text.startswith(needle):
            return category
    return None


def charter_category(aircraft: dict, override: str | None = None) -> str | None:
    """Planning class from the airplane family. Engine type, then range, covers a name that is not listed."""
    chosen = (override or '').strip().lower().replace('-', '_').replace(' ', '_')
    aliases = {
        'vlj': 'very_light',
        'very_light_jet': 'very_light',
        'light_jet': 'light',
        'super_light_jet': 'super_light',
        'superlight': 'super_light',
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
    named = _jet_family(aircraft.get('aircraft_name'))
    if named:
        return named
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
        if distance >= 1700:
            return 'super_light'
        if distance >= 1100:
            return 'light'
        return 'very_light'
    if passengers <= 6:
        return 'very_light'
    if passengers <= 7:
        return 'light'
    if passengers <= 8:
        return 'super_light'
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
    """Spreadsheet hourly variable cost times the class factor. A dated verified rate replaces it."""
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
    """Customer total. Hourly variable cost times the class factor, times the flight hours."""
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
    billable = hours * (2 if round_trip else 1)
    minimum = _num(settings.get('minimum_billable_hours'))
    if minimum and billable < minimum:
        billable = minimum
    total = _round_hundred(rate['hourly_rate'] * billable)
    return {
        'status': rate['status'],
        'category': rate['category'],
        'hourly_rate': round(rate['hourly_rate'], 2),
        'billable_hours': round(billable, 2),
        'flight_charge': round(rate['hourly_rate'] * billable, 2),
        'operator_mid': round(rate['hourly_rate'] * billable, 2),
        'before_tax_mid': round(rate['hourly_rate'] * billable, 2),
        'commission_mid': 0,
        'estimate_low': total,
        'estimate_mid': total,
        'estimate_high': total,
        'tax_status': 'included' if domestic or international else 'included',
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
