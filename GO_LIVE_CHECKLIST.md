# GO LIVE CHECKLIST — JetSchool

Everything in the code is built and tested. This is the list of things **you** do
(in dashboards, not in code) to turn each feature on. Do them top to bottom.
Steps 4–7 are optional — the site works without them.

---

## 1. Make yourself admin (2 minutes)

In **Railway → your service → Variables**, add:

```
ADMIN_EMAILS=youremail@example.com
```

Log out and log back in on the site. You are now an admin and can open
`https://jetschoolusa.com/admin` to approve/reject listings.

---

## 2. Cloudflare R2 — listing photos (15 minutes)

Without this, photo uploads are rejected in production (everything else still works).

1. Cloudflare dashboard → **R2** → Create bucket → name it `jetschool-media`.
2. R2 → **Manage R2 API Tokens** → Create token → "Object Read & Write" on that bucket.
3. Bucket → **Settings → Custom Domains** → add `media.jetschoolusa.com` (keep it proxied/orange cloud).
4. In **Railway → Variables**, add:

```
R2_ACCOUNT_ID=<from Cloudflare R2 overview page>
R2_ACCESS_KEY_ID=<from the token you created>
R2_SECRET_ACCESS_KEY=<from the token you created>
R2_BUCKET_NAME=jetschool-media
R2_PUBLIC_BASE_URL=https://media.jetschoolusa.com
```

Verify: visit `https://jetschoolusa.com/api/data-safety` — `media_storage.configured` should be `true`.

---

## 3. DNS sanity check (5 minutes)

In Cloudflare DNS:

- `jetschoolusa.com` and `www` → point at Railway, **DNS only (grey cloud)**.
- `media` → **Proxied (orange cloud)** — this one SHOULD be proxied.

Verify: `https://jetschoolusa.com/api/health` returns the full health JSON (not just `{"status":"ok"}`).

---

## 4. Stripe payments (15 minutes) — optional

The site works without this; listings just skip payment and go straight to admin review.
When you're ready to charge for listings:

1. Stripe dashboard → **Developers → API keys** → copy the live secret key.
2. Stripe → **Developers → Webhooks** → Add endpoint:
   - URL: `https://jetschoolusa.com/api/stripe/webhook`
   - Event: `checkout.session.completed`
   - Copy the **signing secret** (starts with `whsec_`).
3. In **Railway → Variables**, add:

```
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
REQUIRE_PAYMENT_FOR_LISTINGS=true
```

Flow once enabled: user submits listing → pays $50 (monthly) or $150 (6-month) via
Stripe Checkout → webhook marks it paid → it appears in your admin queue for approval.

---

## 5. Google login (20 minutes) — optional

1. Go to [console.cloud.google.com](https://console.cloud.google.com) → create a project.
2. **APIs & Services → OAuth consent screen**: External, app name "JetSchool",
   add links to `https://jetschoolusa.com/privacy` and `https://jetschoolusa.com/terms`
   (both pages already exist).
3. **APIs & Services → Credentials → Create credentials → OAuth client ID**:
   - Type: Web application
   - Authorized redirect URI: `https://jetschoolusa.com/auth/google/callback`
4. In **Railway → Variables**, add:

```
GOOGLE_CLIENT_ID=<client id>
GOOGLE_CLIENT_SECRET=<client secret>
```

The "Google" button on the login/register pages activates automatically once these are set.

---

## 6. Password-reset emails (10 minutes) — optional

Without this, the forgot-password page still works, but the reset link is only
written to Railway logs (you'd have to send it to the user manually).

Easiest: sign up at [resend.com](https://resend.com) (free tier), verify your domain,
then in **Railway → Variables**:

```
RESEND_API_KEY=re_...
MAIL_FROM=JetSchool <noreply@jetschoolusa.com>
```

(Alternative: any SMTP provider via `SMTP_HOST/SMTP_PORT/SMTP_USER/SMTP_PASS`.)

---

## 7. Final verification (5 minutes)

After redeploying with the variables above:

1. `https://jetschoolusa.com/api/health` → shows users/sessions/listings counts.
2. Sign up with a fresh email → land on `/dashboard`.
3. Create a listing with photos → photos upload → dashboard shows it as "pending".
4. Log in with your admin email → `/admin` → approve the listing.
5. The listing appears in public marketplace search.
6. "Forgot password?" on login page → email arrives → reset works.

---

## What's already done in code (nothing for you to do)

- Email/password + Google signup/login/logout, 30-day sessions
- Customer dashboard with listing status + edit/delete
- Listing creation wired to the real API, photo upload to R2, edit mode (`/create-listing?edit=<id>`)
- Admin portal: approve/reject listings, view users
- Stripe checkout + webhook (dormant until step 4)
- Password reset flow (dormant email until step 6)
- Privacy + Terms pages (`/privacy`, `/terms`)
- Production data-safety guards (deploys never touch user data)
