# Stripe Checkout

Hosted Checkout is already wired in [app.py](app.py). The installed SDK is `stripe==7.8.0` in [requirements.txt](requirements.txt), which is below 21.0.0, so `ui_mode` is `hosted` rather than `hosted_page`.

## Values to Replace

No sample-only placeholders are left in the Checkout Session calls. `mode`, `success_url`, `cancel_url`, and `line_items` already use JetSchool values and were kept.

**Files containing these values:**
- [app.py](app.py)

| Field | Current Value | What to Set |
| --- | --- | --- |
| mode | `subscription` | Leave this. Both sessions bill a monthly subscription. |
| success_url | This site's dashboard URL, with `{CHECKOUT_SESSION_ID}` on the team checkout | Leave this. |
| cancel_url | This site's dashboard URL | Leave this. |
| line_items | Inline monthly prices, not `price_...` placeholders | Leave these. |

## Configured Parameters

These parameters were configured in Checkout Studio and are already set on both `stripe.checkout.Session.create` calls.

**Files containing these parameters:**
- [app.py](app.py)

| Parameter | Value |
| --- | --- |
| ui_mode | `hosted` |
| billing_address_collection | `auto` |
| phone_number_collection | `{"enabled": false}` |
| automatic_tax | `{"enabled": false}` |
| allow_promotion_codes | `true` |
| payment_method_collection | `always` |
| submit_type | `auto` |
| saved_payment_method_options | `{"payment_method_save": "enabled"}` |
| integration_identifier | `hosted_web_0003` |
| origin_context | `web` |

## Setup and next steps

Environment variables already match the code. Set them in the host environment, not in the repo:

- `STRIPE_SECRET_KEY` — server only. Find it at https://dashboard.stripe.com/apikeys
- `STRIPE_PUBLISHABLE_KEY` — server only. This app does not use Vite, so it is not prefixed with `VITE_`
- `STRIPE_WEBHOOK_SECRET` — signing secret for the existing webhook

No new routes or files were added. The Checkout Session calls are the broker team checkout and the shared paid-checkout helper in [app.py](app.py). Each one redirects the customer to a Stripe-hosted payment page. `mode` is `subscription`, so a card is collected and a monthly subscription starts. Promotion codes are accepted. Tax calculation is off. Phone collection is off.

Test cards, in Stripe test mode: `4242 4242 4242 4242`, any future expiry, any CVC, any postal code.

Next steps:

- Confirm `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` are set where the app runs.
- Fulfillment for a completed Checkout Session stays on the existing webhook in [app.py](app.py).
- Listing and solo broker payments still open the hosted payment links. Those links are separate from these Checkout Session calls.

Support: https://support.stripe.com and https://docs.stripe.com/mcp
