# JetSchool billing implementation

Stripe remains the payment processor. JetSchool stores a copy of each listing subscription so the site can show, cancel, and reconcile it. This does not rebuild the site and does not change the Stripe Python package (`stripe==7.8.0`, API `2023-10-16`).

## What was already wrong

Listing checkout created a subscription, but a failed cancel left the listing public and able to renew. The price was fixed at $49.99, so the promotional rate was not applied to new subscriptions. Billing period dates were read only from the subscription object. An email address could be used to guess which listing a charge belonged to. A webhook that failed after it was recorded would not be retried.

## Database changes

Startup still uses `create_all` plus `ALTER TABLE ... ADD COLUMN`. Nothing is dropped. Existing rows stay.

`listing_subscriptions` gained:

- `stripe_price_id`, `stripe_product_id`
- `agreed_amount_cents` (the price the customer started at; later invoices do not replace it)
- `amount_cents` (the current Stripe amount)
- `current_period_start`, `next_renewal_at`
- `cancellation_requested_at`, `cancellation_effective_at`, `cancellation_reason`
- `last_payment_at`, `last_reconciled_at`
- `billing_status` (JetSchool billing state)
- `match_class` (`MATCHED`, `UNMATCHED_CUSTOMER`, `UNMATCHED_LISTING`, `ORPHANED`, `CONFLICT`, `CANCELED`)
- `checkout_url`

`user_listings.paused` hides a listing without canceling its fee.

New tables: `checkout_attempts`, `billing_audits`.

A partial unique index, `uq_listing_one_open_subscription`, allows only one open subscription row per listing. If existing production rows already violate that, startup logs the failure and leaves the rows in place.

Listing review status (`pending`, `active`, `rejected`, `suspended`, `sold`, `deleted`, `archived`) stays separate from `billing_status` (`unpaid`, `incomplete`, `active`, `past_due`, `cancellation_pending`, `cancel_at_period_end`, `canceled`, `unpaid_final`).

## Price

New subscriptions are $14.99 per month through December 31, 2026, 11:59:59 p.m. America/Chicago, then $49.99 per month. The server sets the amount. A subscription that already started keeps `agreed_amount_cents`. The promotion date does not call Stripe to change an existing price.

`automatic_tax` stays off. Stripe Tax collects nothing until a registration exists.

## Checkout

`POST /api/listings/<id>/checkout` opens a hosted Checkout Session in subscription mode. Metadata is written on both the session and `subscription_data.metadata`:

- `jetschool_user_id`, `jetschool_listing_id`, `jetschool_billing_type=aircraft_listing`
- the older `user_id`, `listing_id`, and `purpose=listing_fee` keys

The Stripe customer stored on the user is reused. A second customer is not chosen from a shared email address. An open checkout for that listing is reused. An expired session is marked expired so another checkout can start. The listing stays unpaid until Stripe reports a paid session or an active subscription.

## Cancellation

Delete, Mark sold, and Cancel subscription hide that listing and cancel only its Stripe subscription (`prorate=false`, `invoice_now=false`). No refund is created.

If Stripe cannot confirm the cancel, the listing stays off the public site, `billing_status` is `cancellation_pending`, the subscription id is kept, admins are alerted, and the customer is told that billing is not confirmed stopped. The same action can be repeated. A second aircraft is not touched.

Hide listing sets `paused` and leaves the subscription billing.

Admin reject does not cancel or refund. Admin remove defaults to canceling the subscription. `billing=keep` removes the listing and leaves the subscription, and records that choice.

## Customer and admin screens

Dashboard **My billing** lists each listing subscription, price, next renewal, invoices, card update, and cancel. Listing cards can hide, mark sold, or delete.

Admin **Billing** shows the recurring estimate, collected totals, failed payments, refunds, and reconciliation classes. Matching and canceling require confirmation. A Stripe Dashboard link is on each row for emergencies. Refresh from Stripe does not cancel anything and does not match by email.

## Webhooks

`POST /api/stripe/webhook` verifies `STRIPE_WEBHOOK_SECRET` in production. Handled events include:

- `checkout.session.completed`
- `checkout.session.async_payment_succeeded`
- `checkout.session.async_payment_failed`
- `checkout.session.expired`
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.paid`
- `invoice.payment_failed`
- `invoice.payment_action_required`
- `charge.refunded`, `refund.created`, `refund.updated`
- `charge.dispute.created`, `charge.dispute.closed`
- `radar.early_fraud_warning.created`

A duplicate event is ignored. If storing the event fails, the event id is released and the response is HTTP 500 so Stripe retries. An older event does not overwrite a newer status. Billing periods are read from the subscription item first, then from the subscription object for API `2023-10-16`.

A failed renewal stays public for 7 days, then the listing is suspended. The billing row remains. One failed attempt does not cancel the Stripe subscription.

## Reconciliation

`POST /api/admin/billing/reconcile` reads Stripe and stores subscriptions it can tie to a listing by subscription id or metadata. It does not cancel and does not match by email.

`POST /api/internal/billing/reconcile` with header `X-Billing-Reconcile-Token` updates status, period, and price on subscriptions that are already matched. It does not assign a customer or cancel. Set `BILLING_RECONCILE_TOKEN` and call it from a Railway cron if you want that on a schedule. Opening admin Billing does not run that sync by itself.

Manual match checks that the listing exists, refuses a second open subscription on that listing, and writes a billing audit row.

## Environment

Required for live billing:

- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `DATABASE_URL` (Railway Postgres)

Optional:

- `STRIPE_PORTAL_CONFIGURATION_ID` for Update payment method
- `BILLING_RECONCILE_TOKEN` for the scheduled sync
- `PUBLIC_BASE_URL` for the Checkout return URL

## Migration

Deploy the code and restart the Railway process. `init_db` adds the columns and tables. It does not delete users, listings, or billing rows. Do not run a separate destructive migration.

## Rollback

Redeploy the previous release. New columns and tables can stay; the older code does not read them. Subscriptions already canceled in Stripe stay canceled. Rows left in `cancellation_pending` still need a person to confirm them in Stripe or by repeating the cancel action.

## Tests

`env -u STRIPE_SECRET_KEY python -m unittest tests.test_product -q` — 66 tests, OK. No live charges and no live cancels. Covered cases include promotional and regular prices, agreed price retention, two subscriptions for one customer, checkout metadata, reused customers, failed and recovered webhooks, duplicate and out-of-order events, delete and sold canceling only one subscription, Stripe downtime during cancel, pause without cancel, manual match conflicts, grace-period suspension, and unauthorized cancel.

`gunicorn app:app --check-config` loads the app with the Procfile command.

## Still outside this repository

- Restart Railway after deploy so Postgres gets the new columns.
- In the Stripe Dashboard webhook endpoint, add `checkout.session.expired`, `checkout.session.async_payment_failed`, `customer.subscription.created`, and `invoice.payment_action_required` if they are not already selected.
- Subscriptions created before listing metadata existed will show under Reconciliation until you match them. Do not expect the site to guess from an email.
- A subscription that was left running after an older delete must be canceled from Admin Billing or the Stripe Dashboard. A restart does not cancel it.
- Update payment method needs a Customer Portal configuration if `STRIPE_PORTAL_CONFIGURATION_ID` is not set.
- Stripe Tax stays off until you add a registration. Do not turn on `automatic_tax` before that.

## Production status

Not ready until the Railway restart, the webhook event list, and a manual pass over unmatched live subscriptions are done. The relationships, cancellation, and webhook sync are covered by the automated tests above. They were not run against the live Stripe account.
