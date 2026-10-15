# JetSchool production audit

Status: **READY EXCEPT FOR EXTERNAL CONFIGURATION**

The application runs from root `app.py` on Railway, stores accounts and listings in PostgreSQL, and keeps listing media in Cloudflare R2. Payments, email, media, and admin access stay off until the environment variables below are set. The test suite in `tests/test_product.py` passed locally against a temporary SQLite database (11 tests). Live Stripe charges, R2 uploads, and outbound email were not exercised here because those credentials are not in this environment.

## What already worked

- Email and password accounts, `jet_session` cookie sessions, logout, and password reset when mail is configured.
- Google login when `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set.
- Seller listing create, edit, photo and video upload, dashboard status, and admin approve or reject.
- Public search shows approved public listings only. The aircraft spreadsheet stays off public APIs.
- Aircraft performance profiles and the airport list in PostgreSQL.
- The homepage finder, range map (Esri tiles, no API key), and listing fee checkout skeleton.
- Production safety rules in `db.py`: startup only adds tables and columns. It does not delete user data.

## What was unfinished and is now in the product

- One server-side listing price: **$14.99** through December 31, 2026, 11:59 p.m. America/Chicago, then **$49.99**. The browser cannot set the amount.
- Listing visibility: `public`, `broker_only`, and `private`. Broker-only aircraft are not on the public marketplace or public listing pages. Buyers get a 403 on `/off-market`.
- Extra listing facts (registration, engine hours, avionics, paint year, interior year, and related fields) stored on the listing and linked to the performance profile instead of copied into a second aircraft table.
- Admin audit rows for approve, reject, suspend, resubmit, and private notes. An admin cannot approve their own listing.
- A rejected paid listing can be sent back for review without a second charge.
- “Best airplane for me” ranks approved public listings and explains the score. Turning a category off removes it from the rank and leaves the fact visible.
- Broker directory and map from broker profiles (company, city or airport, specialties, bio, verified flag).
- Charter estimates from performance data, plus a real operator fleet. Customers can **Request to book**. Status stays `requested` until the operator accepts. Empty fleet means nothing is offered as available.
- Homepage paths: find an aircraft, sell, find a broker, charter, and the personalized match.
- Public listing pages with a title, description, and Open Graph tags. Admin, dashboard, and off-market pages send `noindex`.
- Login and signup rate limiting. Login `next` URLs must stay on this site.

## Database changes

Additive only. Existing rows are kept.

New columns on `users`: `roles`, broker profile fields (`broker_bio`, `broker_specialties`, `broker_website`, `broker_years`, `broker_verified`, `broker_state`, `broker_country`, `broker_lat`, `broker_lon`, `broker_image_url`).

New columns on `user_listings`: `serial_number`, `registration`, `variant`, `engine_program`, `engine_hours`, `engine_cycles`, `maintenance_status`, `avionics`, `paint_year`, `interior_year`, `passenger_config`, `admin_notes`. `market` now stores `public`, `broker_only`, or `private`. Older `off_market` values are treated as broker-only.

New tables: `listing_audits`, `stripe_events`, `charter_operators`, `charter_aircraft`, `charter_blocks`, `charter_bookings`, `charter_inquiries`.

## Routes

| Path | Who |
|---|---|
| `/match`, `POST /api/match` | Anyone. Ranks public listings. |
| `/marketplace` | Anyone. Approved public listings. |
| `/listing/<id>` | Anyone, public approved listings only. |
| `/off-market` | Broker or admin. |
| `/brokers` | Anyone. Broker directory and map. |
| `/charter`, `POST /api/charter/estimate` | Anyone. Performance estimate, not a booking. |
| `GET /api/charter/available` | Anyone. Operator aircraft only. |
| `POST /api/charter/book` | Anyone. Creates status `requested`. |
| `/charter/fleet` | Charter operator or admin. |
| `POST /api/charter/fleet/<id>/block` | That operator or admin. |
| `POST /api/charter/bookings/<id>/status` | That operator or admin. |
| `GET /api/pricing/listing` | Anyone. Current fee. |
| `POST /api/listings/<id>/resubmit` | Owner. |
| `POST /api/admin/listings/<id>/suspend` | Admin. |
| `POST /api/admin/listings/<id>/notes` | Admin. Private. |
| `GET /api/admin/listings/<id>/audit` | Admin. |
| `GET /api/me/charter-bookings` | Signed-in customer. |

## Environment variables

Already documented in `.env.example`. Nothing new is required for the app to boot.

| Variable | Needed for |
|---|---|
| `DATABASE_URL` | Railway sets this when Postgres is attached. |
| `SECRET_KEY` | Flask session signing. Set a long random value. |
| `ADMIN_EMAILS` | Your login becomes admin. |
| `REQUIRE_PAYMENT_FOR_LISTINGS=true` | Charge the listing fee before review. |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | Checkout and the signed webhook. |
| `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `R2_PUBLIC_BASE_URL` | Listing photos and video. Production refuses local disk. |
| `RESEND_API_KEY` or `SMTP_HOST` plus `MAIL_FROM` | Password reset, listing decisions, charter updates. |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Optional Google login. |

The map uses Esri’s dark canvas tiles. No map API key.

## What you configure outside Cursor

### Railway

1. Open the Jetschool service. Confirm `DATABASE_URL` is linked from Postgres.
2. Set `SECRET_KEY`, `ADMIN_EMAILS` (your email), and `REQUIRE_PAYMENT_FOR_LISTINGS=true` when you want to charge.
3. Add the Stripe and R2 variables from the table above.
4. Add Resend or SMTP if you want email.
5. Merge this branch to `main`. Railway deploys `main`. The app adds the new columns on startup. It does not wipe listings or users.
6. Log out and back in so `ADMIN_EMAILS` can mark your account admin.
7. Open `https://jetschoolusa.com/api/health` and confirm `db_ok` is true and `database_type` is `postgresql`.

### Cloudflare R2

1. Bucket `jetschool-media` (or the name you put in `R2_BUCKET_NAME`).
2. API token with object read and write on that bucket.
3. Public custom domain `media.jetschoolusa.com` proxied (orange cloud).
4. Put the token values in the Railway `R2_*` variables.
5. DNS for `jetschoolusa.com` and `www` stays DNS-only toward Railway.

### Stripe

1. Use a live secret key in `STRIPE_SECRET_KEY` when you are ready to charge real cards. Use a test key until then.
2. Webhook endpoint: `https://jetschoolusa.com/api/stripe/webhook`
3. Event: `checkout.session.completed`
4. Copy the signing secret to `STRIPE_WEBHOOK_SECRET`.
5. Leave the amount off the webhook. The server sets $14.99 or $49.99.
6. Set `REQUIRE_PAYMENT_FOR_LISTINGS=true`.

## Checks that passed here

`python3 -m unittest tests.test_product -v` — 11 tests, all passed.

Covered: signup, login, logout, wrong password, public versus broker-only listings, buyer blocked from off-market, broker allowed, cross-account edit blocked, non-admin blocked from admin, admin cannot approve their own listing, reject then resubmit without a second charge, score weights, charter request then operator confirm, duplicate Stripe event id, and the listing fee ignoring a client-supplied amount.

Not run against production: a real Stripe card payment, an R2 upload on Railway, and a delivered email. Those need the credentials above.

## Limits that are only external

- No listing fee is collected until Stripe keys and `REQUIRE_PAYMENT_FOR_LISTINGS=true` are set. Until then a new listing goes straight to review.
- Photos and video are rejected in production until R2 is configured. Local development can store files on disk. Production will not.
- Email is skipped, and the event is logged, until Resend or SMTP is set.
- The broker map stays empty until a user sets role Broker and a city or airport.
- Charter “Request to book” only lists aircraft an operator added. Performance estimates on the charter page are estimates, not live availability and not a confirmation.
- `broker_verified` is not self-serve. It is stored for an admin to set. The directory does not call anyone verified unless that flag is true.
- There is no third-party charter inventory feed. The fleet tables are the feed. A later API can write the same tables.
