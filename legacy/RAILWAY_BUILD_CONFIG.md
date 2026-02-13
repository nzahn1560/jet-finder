# Railway Build Configuration

## ✅ Flask-CORS Already Included

`Flask-CORS==4.0.0` is already in `legacy/requirements_production.txt` (line 5).

## Railway Configuration

### Option 1: Railway Dashboard Settings (Recommended)

In Railway dashboard for your service:

1. **Root Directory**: Set to `legacy/`
2. **Build Command**: `pip install -r requirements_production.txt`
3. **Start Command**: `gunicorn app_production:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`

### Option 2: Using railway.toml

If Railway detects `legacy/railway.toml`, it will:
- Build from `legacy/` directory
- Run build command: `pip install -r requirements_production.txt`
- Start with: `gunicorn app_production:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`

### Option 3: Using nixpacks.toml

If Railway detects `legacy/nixpacks.toml`, it will:
- Use Nixpacks builder
- Install dependencies from `requirements_production.txt`
- Start with gunicorn

## Verification

After deployment, check Railway logs for:
```
Collecting Flask-CORS==4.0.0
  Downloading Flask_CORS-4.0.0-py3-none-any.whl
Successfully installed Flask-CORS-4.0.0
```

## Current Requirements

All dependencies in `legacy/requirements_production.txt`:
- Flask==3.0.0
- **Flask-CORS==4.0.0** ✅
- Werkzeug==3.0.1
- psycopg2-binary==2.9.9
- SQLAlchemy==2.0.23
- stripe==7.8.0
- Flask-Limiter==3.5.0
- redis==5.0.1
- python-dotenv==1.0.0
- gunicorn==21.2.0
