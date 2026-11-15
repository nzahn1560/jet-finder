"""One place that decides what a new listing costs.

The server sets the amount. The browser does not.
A new public listing is free through December 31, 2026, 11:59:59 p.m. America/Chicago.
That listing expires December 31, 2027, 11:59:59 p.m. America/Chicago.
$49.99 per month for a listing that starts on or after January 1, 2027.
A subscription already in Stripe keeps the amount it agreed to.
"""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

LISTING_FEE_CENTS = 4999
PROMO_LISTING_FEE_CENTS = 0
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


def listing_price_cents(now: datetime | None = None) -> int:
    """Cents to charge for a new aircraft listing. Zero during the free window."""
    if _chicago(now) <= PROMO_ENDS:
        return PROMO_LISTING_FEE_CENTS
    return LISTING_FEE_CENTS


def free_listing_expires_at() -> datetime:
    """UTC time when a free listing comes off the site."""
    return FREE_LISTING_EXPIRES.astimezone(timezone.utc).replace(tzinfo=None)


def listing_price(now: datetime | None = None) -> dict:
    """Display payload for the listing form and for Stripe."""
    cents = listing_price_cents(now)
    free = cents == 0
    promotional = cents != LISTING_FEE_CENTS
    if free:
        label = (
            'Listing is free through December 31, 2026. '
            'The listing expires December 31, 2027. '
            'Wait 1-5 business days for approval.'
        )
    else:
        label = 'Wait 1-5 business days for approval.'
    return {
        'currency': 'usd',
        'amount_cents': cents,
        'amount_dollars': cents / 100,
        'regular_cents': LISTING_FEE_CENTS,
        'regular_dollars': LISTING_FEE_CENTS / 100,
        'promotional': promotional,
        'free': free,
        'expires_on': '2027-12-31' if free else None,
        'interval': 'month',
        'label': label,
    }
