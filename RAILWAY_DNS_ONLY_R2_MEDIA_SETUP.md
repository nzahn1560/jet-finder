# Production architecture: Railway DNS-only + Cloudflare R2 media

This is the canonical setup for jetschoolusa.com.

```
                        ┌──────────────────────────────────────┐
   browser  ─────────►  │  jetschoolusa.com  (DNS ONLY)         │  ─────►  Railway Flask app
                        │  No Cloudflare proxy on this domain   │           + Railway PostgreSQL
                        └──────────────────────────────────────┘
                        ┌──────────────────────────────────────┐
   browser  ─────────►  │  media.jetschoolusa.com  (Cloudflare) │  ─────►  Cloudflare R2 bucket
                        │  Proxied, immutable cache             │           (listing photos/videos)
                        └──────────────────────────────────────┘
```

**Why split?** Cloudflare's proxy was caching/interfering with the dynamic
Flask app + API. Going DNS-only on the apex fixes that. R2 still gets us
massive savings on media bandwidth (Cloudflare's egress is free for R2 → CDN
→ browser), which is the actual cost risk for a listings site.

---

## 1. DNS setup (Cloudflare DNS tab)

| Hostname | Type | Target | Proxy |
|---|---|---|---|
| `jetschoolusa.com` (apex / `@`) | CNAME | `<your-app>.up.railway.app` | **DNS only** (gray cloud) |
| `www.jetschoolusa.com` | CNAME | `<your-app>.up.railway.app` | **DNS only** (gray cloud) |
| `media.jetschoolusa.com` | CNAME | (added automatically when you connect a custom domain in R2) | **Proxied** (orange cloud) |

In Railway → your service → **Settings** → **Domains**, add `jetschoolusa.com`
and `www.jetschoolusa.com`. Railway gives you the CNAME target for each.

Verify after a few minutes:

```bash
dig +short jetschoolusa.com CNAME
# Should resolve to a Railway target, not Cloudflare IPs only.

curl -sI https://jetschoolusa.com/api/health | head -5
# Should NOT include `server: cloudflare`.
```

---

## 2. Cloudflare R2 bucket setup

1. Cloudflare dashboard → **R2** → **Create bucket** → name it (e.g. `jetschool-media`).
2. Open the bucket → **Settings** → **Public access** → **Connect Domain** → enter
   `media.jetschoolusa.com`. This auto-creates the DNS record in step 1 above.
3. Bucket → **Settings** → **CORS Policy** → paste:

```json
[
  {
    "AllowedOrigins": ["https://jetschoolusa.com", "https://www.jetschoolusa.com"],
    "AllowedMethods": ["GET", "PUT", "HEAD"],
    "AllowedHeaders": ["*"],
    "MaxAgeSeconds": 3600
  }
]
```

4. **R2 → Manage R2 API Tokens → Create API token**:
   - Permissions: **Object Read & Write**
   - Scope: this bucket only
   - Save **Access Key ID**, **Secret Access Key**, and **Account ID**.

---

## 3. Railway environment variables

Set these on your Flask service (Railway → service → **Variables**):

| Variable | Value | Notes |
|---|---|---|
| `FLASK_ENV` | `production` | Turns on safety guards + Secure cookies |
| `DATABASE_URL` | (auto-attached) | Set automatically when Postgres plugin is linked |
| `R2_ACCOUNT_ID` | from Cloudflare R2 dashboard | |
| `R2_ACCESS_KEY_ID` | API token Access Key ID | |
| `R2_SECRET_ACCESS_KEY` | API token Secret Access Key | |
| `R2_BUCKET_NAME` | `jetschool-media` (your bucket name) | |
| `R2_ENDPOINT` | optional | defaults to `https://<account>.r2.cloudflarestorage.com` |
| `R2_PUBLIC_BASE_URL` | `https://media.jetschoolusa.com` | the URL the browser fetches |

Then **Redeploy**.

---

## 4. Verify after deploy

Open these on the live domain:

| URL | What you want to see |
|---|---|
| `https://jetschoolusa.com/api/health` | `db_ok: true`, `database_type: 'postgresql'`, no `server: cloudflare` header |
| `https://jetschoolusa.com/api/data-safety` | `is_production: true`, `media_storage: 'cloudflare_r2'`, `r2.r2_configured: true`, `r2.r2_public_base_url: 'https://media.jetschoolusa.com'` |
| `https://jetschoolusa.com/api/data-source` | `database_connected: true`, both `aircraft_source` and `airports_source` = `postgres` |

If `media_storage` says `not_configured`, R2 env vars are missing or wrong.
If `media_storage` says `local_dev_fallback`, you're not actually in production mode.

---

## 5. Upload flow (what the frontend does)

1. User picks photos/videos in `create-listing.html` → submits the listing first
   (so we have a `listing_id`).
2. Frontend POSTs each file to **`/api/listings/<listing_id>/media`** as
   `multipart/form-data`, field name `file` (one per request) or `files` (many).
   ```js
   const fd = new FormData();
   fd.append('file', fileInput.files[0]);
   await fetch('/api/listings/' + listingId + '/media', {
     method: 'POST',
     credentials: 'include',
     body: fd,
   });
   ```
3. Backend validates the file, uploads to R2 with `Cache-Control: public, max-age=31536000, immutable`,
   stores the metadata row in `listing_media`, and returns the public URL.
4. Listing pages render `<img src="https://media.jetschoolusa.com/listings/{id}/photos/{uuid}.jpg">`.

### Limits (configurable in `r2_storage.py`)

| Limit | Default |
|---|---|
| Photo content types | `image/jpeg`, `image/png`, `image/webp`, `image/gif` |
| Video content types | `video/mp4`, `video/webm`, `video/quicktime`, `video/mpeg` |
| Photo max size | 12 MB |
| Video max size | 250 MB |
| Photos per listing | 40 |
| Videos per listing | 5 |

---

## 6. Frontend cost-saving rules (enforce these)

1. **Listing cards** show ONLY `cover_image` from `/api/listings/me` or `/api/user-listings`.
   Don't render all 40 photos in the search/grid view.
2. **Listing detail page** lazy-loads media: call `/api/listings/<id>/media`
   only when the user opens the page; render `<img loading="lazy">`.
3. **Videos**: render `<video preload="none" poster="{thumbnail}">` and only call
   `.play()` after a user click. Never autoplay video on lists.
4. **Object keys are unique** (`listings/{id}/photos/{uuid}.jpg`), so we set
   `Cache-Control: public, max-age=31536000, immutable` on upload and never
   need to invalidate.
5. **Custom domain** (`media.jetschoolusa.com`) makes Cloudflare cache the
   response globally → photos are nearly free to serve on repeat views.

---

## 7. Local development (no R2 credentials)

If you don't set the R2 env vars locally, uploads fall back to
`static/uploads/dev/listings/.../{uuid}.ext` and the public URL is
`/static/uploads/dev/...`. This is dev-only — in production the same code
path **raises** instead of falling back (so we never accidentally serve
listing media from Railway disk).

To disable the fallback locally, set `FLASK_ENV=production`.

---

## 8. Backups for media

R2 bytes are not in our Postgres backup (`pg_dump`), so:

- Enable R2 **Versioning** on the bucket so deleted objects can be recovered.
- For full disaster recovery, use Cloudflare's R2 → **Replication** to copy
  objects to a second bucket in another account/region.
- The Postgres `listing_media` table is the source of truth for which R2
  objects belong to which listing — keep it backed up per `BACKUPS.md`.

---

## 9. Frontend checklist before launch

- [ ] Upload UI POSTs to `/api/listings/<id>/media` with `credentials:'include'`.
- [ ] Search/grid pages render `cover_image` only (not full gallery).
- [ ] Detail page fetches `/api/listings/<id>/media` lazily and uses
      `<img loading="lazy">`.
- [ ] Videos use `<video preload="none">` and only load on click.
- [ ] No `<img src="/static/uploads/...">` references remain in templates
      (they would mean we're serving from Railway disk, which we don't).
