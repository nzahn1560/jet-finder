# Railway Start Command

## Copy and Paste This:

```
gunicorn app_production:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --access-logfile - --error-logfile -
```

## How to Set in Railway:

1. Go to Railway Dashboard
2. Click on your service
3. Go to **Settings** tab
4. Scroll to **"Start Command"**
5. Paste the command above
6. Click **"Save"**

## Alternative (Simpler Version):

If you want a simpler version without access/error logs:

```
gunicorn app_production:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```

## What Each Part Does:

- `gunicorn` - Python WSGI HTTP server
- `app_production:app` - Module:variable (app_production.py file, app variable)
- `--bind 0.0.0.0:$PORT` - Listen on all interfaces, use Railway's PORT
- `--workers 2` - Run 2 worker processes (handles multiple requests)
- `--timeout 120` - Request timeout (120 seconds)
- `--access-logfile -` - Log access to stdout (Railway logs)
- `--error-logfile -` - Log errors to stdout (Railway logs)

## Note:

Railway will auto-detect the `Procfile` if it exists in the root directory.
Since your Procfile is in `legacy/`, you need to either:
1. Set Root Directory to `legacy` (recommended), OR
2. Manually set the Start Command above
