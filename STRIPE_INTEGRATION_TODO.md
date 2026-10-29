# Stripe Checkout

Hosted Checkout is already wired in [app.py](app.py). Customers are redirected to a Stripe-hosted payment page. The installed SDK is `stripe==7.8.0` in [requirements.txt](requirements.txt), which is below 21.0.0, so `ui_mode` is `hosted`. SDK 21.0.0 and above would use `hosted_page` instead.

A listing fee is $49.99. A broker account is $19.99 a month. A broker team is $19.99 a month. Coupon codes are accepted at Checkout.

## Values to Replace

No sample-only placeholders are left in the Checkout Session calls. `mode`, `success_url`, `cancel_url`, and `line_items` already use live JetSchool values and were not replaced.

**Files:**
- [app.py](app.py)

| Field | Current value | What to set |
| --- | --- | --- |
| mode | `payment` for a listing. `subscription` for a broker account and a broker team. | Leave these. |
| success_url | Dashboard URL on this site. Broker checkout keeps `{CHECKOUT_SESSION_ID}`. | Leave these. |
| cancel_url | Dashboard URL on this site. | Leave these. |
| line_items | Inline prices: $49.99 once for a listing, $19.99 per month for a broker account, $19.99 per month for a broker team. | Leave these. They are not `price_...` placeholders. |

## Configured Parameters

These Checkout Studio values are set on the `stripe.checkout.Session.create` calls in [app.py](app.py).

**Files:**
- [app.py](app.py)

| Parameter | Value |
| --- | --- |
| ui_mode | `hosted` |
| billing_address_collection | `auto` |
| phone_number_collection | `{"enabled": true}` |
| automatic_tax | `{"enabled": false}` |
| allow_promotion_codes | `true` |
| payment_method_collection | `always` on the two subscription calls only |
| submit_type | `auto` on the listing-fee payment call only |
| consent_collection | `{"terms_of_service": "required"}` |
| name_collection | individual and business name, both enabled and optional |
| saved_payment_method_options | `{"payment_method_save": "enabled"}` on the listing-fee payment call |
| integration_identifier | `hosted_web_0001` |
| origin_context | `web` |

`payment_method_collection` is omitted on the one-time listing fee. `submit_type` is omitted on the broker subscriptions because Stripe only accepts it when `mode` is `payment`. `saved_payment_method_options` is on the listing fee. A subscription already saves the card for renewal.

Customer, metadata, and subscription metadata stay on the calls so a paid session can still be matched to the listing or the broker account.

## Setup and next steps

Environment variables already match the code and [.env.example](.env.example). Set them in Railway, not in the repo:

- `STRIPE_SECRET_KEY` — server only
- `STRIPE_PUBLISHABLE_KEY` — server only. This app does not use Vite for Checkout.
- `STRIPE_WEBHOOK_SECRET` — signing secret for `https://jetschoolusa.com/api/stripe/webhook`

No new routes were added. The three existing sessions are:

1. `POST /api/listings/<id>/checkout` — $49.99 listing fee, then back to the dashboard.
2. `POST /api/account/broker-checkout` — $19.99 per month broker account.
3. `POST /api/account/team-checkout` — $19.99 per month broker team.

Stripe hosts the payment page. Checkout asks for a phone number, an optional individual or business name, and acceptance of the terms. A promotion code box is shown, and Stripe applies the coupons created in the Dashboard. Tax calculation is off. The webhook marks a listing paid, turns broker access on, and turns it off when the subscription ends, a charge is fully refunded, or a dispute or fraud review is open.

Before the first live checkout, set the Terms of service URL in the Stripe Dashboard to `https://jetschoolusa.com/terms`. Checkout will not start while terms are required and that URL is missing.

Test cards, in Stripe test mode: `4242 4242 4242 4242`, any future expiry, any CVC, any postal code. Do not use those on the live JetschoolUSA account.

Remaining Dashboard steps:

- Webhook endpoint `https://jetschoolusa.com/api/stripe/webhook` with the events already handled in [app.py](app.py), and the signing secret stored as `STRIPE_WEBHOOK_SECRET`.
- Customer Portal, so **Manage billing** can update a card or cancel at the end of the paid month.
- Terms of service URL, required by the Checkout consent setting above.

Support: https://support.stripe.com and https://docs.stripe.com/mcp
