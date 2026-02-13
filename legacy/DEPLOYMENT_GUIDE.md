# JetSchool USA - Deployment Guide

## Overview

This is a Flask-based aircraft marketplace with an intelligent **Match Tool** that ranks listings by how well they match buyer requirements using weighted scoring across 5 categories.

## Quick Start (Local Development)

### Prerequisites
- Python 3.8+
- pip
- Virtual environment (recommended)

### Setup

1. **Create Virtual Environment**
```bash
cd legacy
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

3. **Required Files**
Ensure these files are in the parent directory:
- `Aircraft Data - Aircraft Data (1).csv` (314 aircraft)

4. **Run Locally**
```bash
python app.py
```

Server runs at: `http://localhost:5015`

---

## Features

### 🎯 Match Tool
- **Weighted Scoring**: Rank aircraft by custom category weights
- **5 Categories**: Performance, Condition, Cosmetic, Avionics, Value
- **Percentile-Based**: Scores relative to all available aircraft
- **Top Reasons**: Explains why each aircraft is a good match

### 🔍 Advanced Filtering
- Range, Speed, Passengers, Budget
- Manufacturer, Category
- Year, Altitude, Runway, Cabin Volume
- Annual/Hourly Costs

### 📊 Comparison Tool
- Compare up to 4 aircraft side-by-side
- **Percentile Charts**: Better choices = taller bars (even for cost)
- Visual performance metrics

### 📑 Aircraft Listings
- 314 aircraft from CSV data
- Pagination (12 per page)
- Clean listing cards with expandable performance profiles
- Match scores with category breakdowns

---

## Railway Deployment

### Step 1: Prepare Repository

1. **Push to GitHub**
```bash
git add .
git commit -m "Prepare for Railway deployment"
git push origin main
```

2. **Required Files in Repo**
- `legacy/app.py` (main Flask app)
- `legacy/requirements.txt`
- `legacy/Procfile` (create if missing)
- `Aircraft Data - Aircraft Data (1).csv` (in project root)
- `legacy/templates/` (all HTML templates)
- `legacy/static/` (CSS, JS, images)
- `legacy/match_scoring.py` (Match Tool engine)
- `legacy/match_tool_api.py` (API endpoints)

### Step 2: Create Procfile

In `legacy/` directory, create `Procfile`:
```
web: gunicorn app:app --bind 0.0.0.0:$PORT
```

### Step 3: Update requirements.txt

Ensure `legacy/requirements.txt` includes:
```
Flask==2.3.0
gunicorn==21.2.0
pandas==2.0.0
numpy==1.24.0
python-dotenv==1.0.0
stripe==5.4.0
```

### Step 4: Railway Setup

1. **Create New Project**
   - Go to [Railway.app](https://railway.app)
   - Click "New Project"
   - Choose "Deploy from GitHub repo"
   - Select your `jet-finder` repository

2. **Configure Root Directory**
   - Settings → Root Directory: `legacy`
   - This tells Railway the app is in the `legacy/` folder

3. **Set Environment Variables**
   - Settings → Variables
   - Add:
     ```
     FLASK_ENV=production
     SECRET_KEY=your-secure-random-key-here
     PORT=5015
     ```

4. **Deploy**
   - Railway auto-detects Python and runs:
     ```bash
     pip install -r requirements.txt
     gunicorn app:app --bind 0.0.0.0:$PORT
     ```

5. **Get Domain**
   - Settings → Generate Domain
   - Your app will be at: `https://your-app.up.railway.app`

---

## Database Setup (Optional - For User Listings)

Currently using CSV data. To add user-submitted listings:

### Option 1: SQLite (Simple)
Already configured in `app.py`:
```python
conn = sqlite3.connect('instance/jet_finder.db')
```

### Option 2: Railway Postgres (Production)

1. **Add Postgres to Railway**
   - In your Railway project
   - Click "New" → "Database" → "Add PostgreSQL"
   - Copy `DATABASE_URL`

2. **Update app.py**
```python
import os
import psycopg2

DATABASE_URL = os.environ.get('DATABASE_URL')
conn = psycopg2.connect(DATABASE_URL)
```

3. **Add to requirements.txt**
```
psycopg2-binary==2.9.9
```

4. **Run Migrations**
```bash
# Create tables
python migrations/001_init.py
```

---

## API Endpoints

### Match Tool API

**POST** `/api/match-tool/rank`
Rank aircraft by match score
```json
{
  "aircraft": [...],
  "profile": {
    "performance_profile_id": 1,
    "weight_performance": 0.25,
    "weight_condition": 0.25,
    "weight_cosmetic": 0.15,
    "weight_avionics": 0.10,
    "weight_value": 0.25
  }
}
```

**GET** `/api/match-tool/categories`
Get category definitions

**GET** `/api/match-tool/health`
Health check

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_ENV` | Environment | `development` |
| `SECRET_KEY` | Session secret | (generate secure key) |
| `PORT` | Server port | `5015` |
| `DATABASE_URL` | Database connection | SQLite |
| `STRIPE_SECRET_KEY` | Stripe payments | (optional) |
| `STRIPE_PUBLISHABLE_KEY` | Stripe public key | (optional) |

### Generate Secure Secret Key
```python
import secrets
print(secrets.token_hex(32))
```

---

## Troubleshooting

### CSV Not Found
**Error**: `[Errno 2] No such file or directory: 'Aircraft Data - Aircraft Data (1).csv'`

**Fix**: CSV path in `app.py` line 1102:
```python
df = pd.read_csv('../Aircraft Data - Aircraft Data (1).csv')
```
Ensure CSV is in project root (one level up from `legacy/`)

### Import Errors
**Error**: `ModuleNotFoundError: No module named 'marketplace'`

**Fix**: These are in `legacy/` folder:
- Move to `legacy/` directory: `cd legacy`
- Or update imports to use absolute paths

### Match Tool Not Working
**Error**: Match scores not calculating

**Check**:
1. API endpoint registered: Look for log `✅ Match Tool API registered at /api/match-tool/*`
2. NumPy installed: `pip install numpy==1.24.0`
3. Browser console for JavaScript errors

### Port Already in Use
**Error**: `Address already in use`

**Fix**:
```bash
# Find process
lsof -ti:5015 | xargs kill -9

# Or change port in app.py
app.run(debug=True, host="0.0.0.0", port=5016)
```

---

## Performance Optimization

### For Production

1. **Use Gunicorn with Workers**
```bash
gunicorn app:app --workers 4 --bind 0.0.0.0:$PORT
```

2. **Enable Caching**
```python
from flask_caching import Cache
cache = Cache(app, config={'CACHE_TYPE': 'simple'})
```

3. **Compress Responses**
```python
from flask_compress import Compress
Compress(app)
```

4. **Database Connection Pool**
```python
from sqlalchemy import create_engine
engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20)
```

---

## Security Checklist

- [ ] Set secure `SECRET_KEY` (not default)
- [ ] Use HTTPS in production (Railway provides this)
- [ ] Validate all user inputs
- [ ] Rate limit API endpoints
- [ ] Enable CSRF protection
- [ ] Set secure cookie flags
- [ ] Update dependencies regularly

---

## Monitoring

### Railway Logs
```bash
# View live logs
railway logs
```

### Health Check Endpoint
```bash
curl https://your-app.up.railway.app/api/match-tool/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "match-tool-api",
  "version": "1.0.0"
}
```

---

## Support

### Documentation
- Flask: https://flask.palletsprojects.com/
- Railway: https://docs.railway.app/
- Match Tool API: `/api/match-tool/categories`

### Common Issues
1. **314 aircraft not loading**: Check CSV path
2. **Match scores = 0**: Weights must sum to 100%
3. **Filters not working**: Check JavaScript console
4. **Compare charts empty**: Need Chart.js loaded

---

## Next Steps

1. **Custom Domain**: Railway Settings → Add custom domain
2. **SSL Certificate**: Auto-provided by Railway
3. **Database**: Add Postgres for user listings
4. **Auth**: Implement user authentication (Supabase/Auth0)
5. **Payments**: Configure Stripe for premium features
6. **Analytics**: Add Google Analytics or Plausible

---

## License

Proprietary - JetSchool USA

## Version

**v1.0.0** - Match Tool with Percentile Ranking (January 2026)
