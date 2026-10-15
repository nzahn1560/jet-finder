"""One place that decides what a listing costs.

The promotional price is $14.99 through December 31, 2026 in America/Chicago.
At January 1, 2027 12:00:00 AM Chicago time the price becomes $49.99.
The server clock decides. The browser does not.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

CHICAGO = ZoneInfo('America/Chicago')
PROMO_ENDS = datetime(2027, 1, 1, 0, 0, 0, tzinfo=CHICAGO)
REGULAR_CENTS = 4999
PROMO_CENTS = 1499


def listing_price_cents(now: datetime | None = None) -> int:
    """Cents to charge for one aircraft listing at `now` (Chicago if naive)."""
    moment = now or datetime.now(CHICAGO)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=CHICAGO)
    else:
        moment = moment.astimezone(CHICAGO)
    if moment < PROMO_ENDS:
        return PROMO_CENTS
    return REGULAR_CENTS


def listing_price(now: datetime | None = None) -> dict:
    """Display payload for the listing form and for Stripe."""
    cents = listing_price_cents(now)
    promo = cents == PROMO_CENTS
    return {
        'currency': 'usd',
        'amount_cents': cents,
        'amount_dollars': cents / 100,
        'regular_cents': REGULAR_CENTS,
        'regular_dollars': REGULAR_CENTS / 100,
        'promotional': promo,
        'promo_ends': '2026-12-31T23:59:59-06:00',
        'label': 'Launch pricing through December 31, 2026.' if promo else 'Listing fee',
    }
