"""One place that decides what a listing costs.

A listing is $49.99. The server sets the amount. The browser does not.
"""
from __future__ import annotations

from datetime import datetime

LISTING_FEE_CENTS = 4999


def listing_price_cents(now: datetime | None = None) -> int:
    """Cents to charge for one aircraft listing."""
    return LISTING_FEE_CENTS


def listing_price(now: datetime | None = None) -> dict:
    """Display payload for the listing form and for Stripe."""
    cents = listing_price_cents(now)
    return {
        'currency': 'usd',
        'amount_cents': cents,
        'amount_dollars': cents / 100,
        'regular_cents': cents,
        'regular_dollars': cents / 100,
        'promotional': False,
        'label': 'Listing fee',
    }
