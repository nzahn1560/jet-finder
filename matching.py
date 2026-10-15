"""Rank approved public listings for one buyer.

Hard limits remove aircraft that cannot do the trip. Everything else is a
score the buyer can turn on or off. Missing facts score as neutral, not zero,
so an aircraft is not punished for a field the seller left blank.
"""
from __future__ import annotations

from typing import Any

COMPONENTS = (
    'mission',
    'value',
    'engine',
    'avionics',
    'interior',
    'paint',
    'airframe',
    'age',
    'performance',
)

DEFAULT_ON = set(COMPONENTS)


def _num(value: Any) -> float | None:
    if value is None or value == '':
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp(score: float) -> int:
    return int(max(0, min(100, round(score))))


def _enabled(preferences: dict) -> set[str]:
    raw = preferences.get('weights')
    if not isinstance(raw, dict) or not raw:
        return set(DEFAULT_ON)
    chosen = {key for key in COMPONENTS if raw.get(key)}
    return chosen or set(DEFAULT_ON)


def qualifies(card: dict, preferences: dict) -> tuple[bool, str | None]:
    """True when the aircraft can do the stated mission."""
    need_range = _num(preferences.get('range_nm'))
    aircraft_range = _num(card.get('range'))
    if need_range and aircraft_range is not None and aircraft_range < need_range:
        return False, 'Range is shorter than the trip.'
    need_seats = _num(preferences.get('passengers'))
    seats = _num(card.get('passengers'))
    if need_seats and seats is not None and seats < need_seats:
        return False, 'Not enough passenger seats.'
    budget = _num(preferences.get('budget'))
    price = _num(card.get('price'))
    if budget and price is not None and price > budget:
        return False, 'Asking price is over the budget.'
    return True, None


def _score_card(card: dict, preferences: dict, prices: list[float]) -> dict[str, int]:
    scores: dict[str, int] = {}
    aircraft_range = _num(card.get('range'))
    need_range = _num(preferences.get('range_nm')) or 0
    if aircraft_range is None:
        scores['mission'] = 70
    elif need_range <= 0:
        scores['mission'] = 80
    else:
        margin = aircraft_range / need_range
        scores['mission'] = _clamp(60 + min(margin, 2) * 20)

    price = _num(card.get('price'))
    if price is None or not prices:
        scores['value'] = 70
    else:
        low, high = min(prices), max(prices)
        if high <= low:
            scores['value'] = 80
        else:
            # Lower asking price scores higher. Spread across the current set.
            scores['value'] = _clamp(100 - ((price - low) / (high - low)) * 70)

    engine_hours = _num(card.get('engine_hours'))
    if engine_hours is None:
        scores['engine'] = 70
    else:
        scores['engine'] = _clamp(100 - min(engine_hours, 8000) / 80)

    scores['avionics'] = 82 if (card.get('avionics') or '').strip() else 60

    interior_year = _num(card.get('interior_year'))
    scores['interior'] = 70 if interior_year is None else _clamp(40 + max(0, interior_year - 1995) * 2)
    paint_year = _num(card.get('paint_year'))
    scores['paint'] = 70 if paint_year is None else _clamp(40 + max(0, paint_year - 1995) * 2)

    hours = _num(card.get('hours'))
    scores['airframe'] = 70 if hours is None else _clamp(100 - min(hours, 15000) / 150)

    year = _num(card.get('year'))
    scores['age'] = 70 if year is None else _clamp(30 + max(0, year - 1980) * 1.6)

    speed = _num(card.get('speed')) or 0
    rng = aircraft_range or 0
    scores['performance'] = _clamp(40 + min(speed, 500) / 10 + min(rng, 4000) / 80)
    return scores


def _words(card: dict, scores: dict[str, int], enabled: set[str]) -> tuple[list[str], list[str]]:
    strengths = []
    tradeoffs = []
    if 'mission' in enabled and scores['mission'] >= 85:
        strengths.append('Covers the trip with range to spare.')
    if 'value' in enabled and scores['value'] >= 80:
        strengths.append('Asking price is strong against the other aircraft for sale.')
    if 'engine' in enabled and scores['engine'] >= 85 and card.get('engine_hours') is not None:
        strengths.append('Engine time still looks favorable.')
    if 'avionics' in enabled and scores['avionics'] >= 80:
        strengths.append('Avionics are described on the listing.')
    if 'paint' in enabled and scores['paint'] < 65 and card.get('paint_year'):
        tradeoffs.append('Paint is older than the other aircraft in this search.')
    if 'interior' in enabled and scores['interior'] < 65 and card.get('interior_year'):
        tradeoffs.append('Interior year is older.')
    if 'performance' in enabled and scores['performance'] < 60:
        tradeoffs.append('Speed or range is modest for this group.')
    if 'value' in enabled and scores['value'] < 50:
        tradeoffs.append('Asking price is high for this group.')
    return strengths[:4], tradeoffs[:3]


def rank_listings(cards: list[dict], preferences: dict | None = None) -> dict:
    """Return ranked listings plus the ones removed by a hard limit."""
    preferences = preferences or {}
    enabled = _enabled(preferences)
    kept = []
    removed = []
    for card in cards:
        ok, reason = qualifies(card, preferences)
        if ok:
            kept.append(card)
        else:
            removed.append({'id': card.get('id'), 'title': card.get('title'), 'reason': reason})
    prices = [p for p in (_num(card.get('price')) for card in kept) if p is not None]
    ranked = []
    for card in kept:
        parts = _score_card(card, preferences, prices)
        used = {key: parts[key] for key in COMPONENTS if key in enabled}
        overall = _clamp(sum(used.values()) / len(used)) if used else 0
        strengths, tradeoffs = _words(card, parts, enabled)
        ranked.append({
            'id': card.get('id'),
            'title': card.get('title'),
            'manufacturer': card.get('manufacturer'),
            'price': card.get('price'),
            'year': card.get('year'),
            'hours': card.get('hours'),
            'location': card.get('location'),
            'range': card.get('range'),
            'passengers': card.get('passengers'),
            'speed': card.get('speed'),
            'image': card.get('image'),
            'overall': overall,
            'scores': {key: parts[key] for key in COMPONENTS},
            'used': sorted(enabled),
            'strengths': strengths,
            'tradeoffs': tradeoffs,
        })
    ranked.sort(key=lambda row: (-row['overall'], row.get('price') or 0, row.get('id') or 0))
    return {'results': ranked, 'excluded': removed, 'weights': sorted(enabled)}
