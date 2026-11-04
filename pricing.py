"""One place that decides what a new listing subscription costs.

The server sets the amount. The browser does not.
$14.99 per month through December 31, 2026, 11:59:59 p.m. America/Chicago.
$49.99 per month for a subscription that starts on or after January 1, 2027.
A subscription already in Stripe keeps the amount it agreed to. This date
change does not modify it.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

LISTING_FEE_CENTS = 4999
PROMO_LISTING_FEE_CENTS = 1499
CHICAGO = ZoneInfo('America/Chicago')
PROMO_ENDS = datetime(2026, 12, 31, 23, 59, 59, tzinfo=CHICAGO)


def listing_price_cents(now: datetime | None = None) -> int:
    """Cents to charge for a new aircraft listing subscription."""
    moment = now or datetime.now(CHICAGO)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=CHICAGO)
    else:
        moment = moment.astimezone(CHICAGO)
    if moment <= PROMO_ENDS:
        return PROMO_LISTING_FEE_CENTS
    return LISTING_FEE_CENTS


def listing_price(now: datetime | None = None) -> dict:
    """Display payload for the listing form and for Stripe."""
    cents = listing_price_cents(now)
    promotional = cents != LISTING_FEE_CENTS
    if promotional:
        label = (
            '$14.99 per month through December 31, 2026. '
            'A new listing on or after January 1, 2027 is $49.99 per month. '
            'A subscription already started keeps its price. '
            'Canceling stops future charges and does not refund a charge already collected. '
            'A listing fee is non-refundable once the listing is approved and published.'
        )
    else:
        label = (
            '$49.99 per month, billed until you cancel. '
            'Canceling stops future charges and does not refund a charge already collected. '
            'A listing fee is non-refundable once the listing is approved and published.'
        )
    return {
        'currency': 'usd',
        'amount_cents': cents,
        'amount_dollars': cents / 100,
        'regular_cents': LISTING_FEE_CENTS,
        'regular_dollars': LISTING_FEE_CENTS / 100,
        'promotional': promotional,
        'interval': 'month',
        'label': label,
    }
