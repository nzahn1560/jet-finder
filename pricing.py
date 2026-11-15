"""One place that decides what a new listing costs.

The server sets the amount. The browser does not.
Checkout charges $49.99 per month. Code 100OFF is entered at Stripe checkout.
A listing paid with that code through December 31, 2026, 11:59:59 p.m. America/Chicago
expires December 31, 2027, 11:59:59 p.m. America/Chicago.
A subscription already in Stripe keeps the amount it agreed to.
"""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

LISTING_FEE_CENTS = 4999
PROMO_LISTING_FEE_CENTS = 1499
LISTING_PROMO_CODE = '100OFF'
CHICAGO = ZoneInfo('America/Chicago')
PROMO_ENDS = datetime(2026, 12, 31, 23, 59, 59, tzinfo=CHICAGO)
FREE_LISTING_EXPIRES = datetime(2027, 12, 31, 23, 59, 59, tzinfo=CHICAGO)


def _chicago(now: datetime | None = None) -> datetime:
    moment = now or datetime.now(CHICAGO)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=CHICAGO)
    else:
        moment = moment.astimezone(CHICAGO)
    return moment


def listing_promo_open(now: datetime | None = None) -> bool:
    """True while 100OFF can make a new listing free."""
    return _chicago(now) <= PROMO_ENDS


def listing_price_cents(now: datetime | None = None) -> int:
    """Cents Stripe charges before a promotion code. The code is not applied here."""
    return LISTING_FEE_CENTS


def free_listing_expires_at() -> datetime:
    """UTC time when a listing paid with 100OFF comes off the site."""
    return FREE_LISTING_EXPIRES.astimezone(timezone.utc).replace(tzinfo=None)


def listing_price(now: datetime | None = None) -> dict:
    """Display payload for the listing form. Checkout still charges amount_cents."""
    cents = listing_price_cents(now)
    promo_open = listing_promo_open(now)
    if promo_open:
        label = (
            'The listing fee is $49.99 per month. '
            'Enter code 100OFF at checkout for a free listing through December 31, 2026. '
            'The listing expires December 31, 2027. '
            'Wait 1-5 business days for approval.'
        )
        note = 'Enter code 100OFF at checkout. The listing expires December 31, 2027.'
    else:
        label = 'Wait 1-5 business days for approval.'
        note = ''
    return {
        'currency': 'usd',
        'amount_cents': cents,
        'amount_dollars': cents / 100,
        'regular_cents': LISTING_FEE_CENTS,
        'regular_dollars': LISTING_FEE_CENTS / 100,
        'promotional': False,
        'free': False,
        'promo_code': LISTING_PROMO_CODE if promo_open else None,
        'expires_on': '2027-12-31' if promo_open else None,
        'note': note,
        'interval': 'month',
        'label': label,
    }
