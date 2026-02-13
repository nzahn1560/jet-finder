# JetSchoolUSA - System Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         RAILWAY PLATFORM                         │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                      Flask Application                      │ │
│  │                        (app.py)                             │ │
│  │                                                             │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐ │ │
│  │  │   Frontend   │  │   API Routes │  │  Match Scoring  │ │ │
│  │  │   (React)    │  │   /api/*     │  │     Engine      │ │ │
│  │  │   Served at  │  │              │  │  (Percentile)   │ │ │
│  │  │      /       │  │              │  │                 │ │ │
│  │  └──────────────┘  └──────────────┘  └─────────────────┘ │ │
│  │                                                             │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐ │ │
│  │  │     Auth     │  │    Admin     │  │  Audit Logging  │ │ │
│  │  │   System     │  │   System     │  │                 │ │ │
│  │  └──────────────┘  └──────────────┘  └─────────────────┘ │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                    │
│                              ▼                                    │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                  PostgreSQL Database                        │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐ │ │
│  │  │  users   │  │ profiles │  │ listings │  │   audit   │ │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └───────────┘ │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Stripe API     │
                    │  - Checkout     │
                    │  - Subscriptions│
                    │  - Webhooks     │
                    └─────────────────┘
```

## Request Flow

### User Registration & Listing Creation

```
User Browser
    │
    ├─► POST /api/auth/register
    │       └─► Create user in DB
    │       └─► Return session
    │
    ├─► POST /api/listings
    │       └─► Create listing (status: draft)
    │       └─► Return listing_id
    │
    ├─► POST /api/listings/{id}/checkout
    │       └─► Create Stripe checkout session
    │       └─► Return checkout URL
    │
    └─► Redirect to Stripe Checkout
            │
            ├─► User pays
            │
            └─► Stripe Webhook → /api/stripe/webhook
                    └─► Update listing (status: pending)
```

### Admin Review Flow

```
Admin Browser
    │
    ├─► POST /api/auth/login (admin account)
    │       └─► Verify is_admin flag
    │       └─► Return session
    │
    ├─► GET /api/admin/listings/pending
    │       └─► Query listings WHERE status='pending'
    │       └─► Return pending listings
    │
    └─► POST /api/admin/listings/{id}/approve
            └─► Update listing (status: active)
            └─► Log audit event
            └─► Listing now public
```

### Match Tool Flow

```
Buyer Browser
    │
    ├─► GET /api/profiles
    │       └─► Return all aircraft profiles
    │
    ├─► POST /api/match
    │       └─► Filter active listings by criteria
    │       └─► Calculate percentile scores
    │       └─► Group into categories
    │       └─► Compute overall match scores
    │       └─► Sort by match score DESC
    │       └─► Generate top reasons
    │       └─► Return ranked listings
    │
    └─► Display results with:
            - Match score (0-100)
            - Category breakdowns
            - Top 3 reasons
```

## Database Schema

```
┌─────────────────────────────────────────────────────────────────┐
│                            users                                 │
├─────────────────────────────────────────────────────────────────┤
│ id (PK)                                                          │
│ email (UNIQUE)                                                   │
│ password_hash                                                    │
│ first_name, last_name, company, phone                           │
│ is_admin, is_active                                             │
│ created_at, updated_at                                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ user_id (FK)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                          listings                                │
├─────────────────────────────────────────────────────────────────┤
│ id (PK)                                                          │
│ user_id (FK → users)                                            │
│ profile_id (FK → performance_profiles)                          │
│ title, description, price, location, contact_email             │
│ year, serial_number, registration                               │
│ total_time, engine1_time, engine1_tbo                           │
│ interior_year, paint_year, avionics_value_estimate             │
│ images, video_url                                               │
│ status (draft/pending/active/rejected/inactive/expired)        │
│ rejection_reason                                                │
│ stripe_customer_id, stripe_subscription_id                      │
│ plan_type, subscription_status, current_period_end             │
│ approved_by (FK → users), approved_at                           │
│ created_at, updated_at                                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ profile_id (FK)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    performance_profiles                          │
├─────────────────────────────────────────────────────────────────┤
│ id (PK)                                                          │
│ manufacturer, model, category                                   │
│ range_nm, cruise_speed_knots, max_altitude                      │
│ max_passengers, cabin_volume, baggage_volume                    │
│ runway_length, fuel_capacity, engine_type                       │
│ typical_price, typical_total_time                               │
│ created_at                                                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        audit_events                              │
├─────────────────────────────────────────────────────────────────┤
│ id (PK)                                                          │
│ user_id (FK → users)                                            │
│ listing_id (FK → listings)                                      │
│ action (e.g., 'LISTING_APPROVED', 'USER_LOGIN')                │
│ details (JSON text)                                             │
│ ip_address                                                      │
│ created_at                                                      │
└─────────────────────────────────────────────────────────────────┘
```

## Match Scoring Algorithm Flow

```
Input: Filtered listings (e.g., profile_id=1, max_price=10M)
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: Extract all values for each metric                      │
│   - ranges = [2040, 1550, 2700, ...]                           │
│   - speeds = [416, 404, 446, ...]                              │
│   - prices = [8500000, 4700000, 17000000, ...]                 │
│   - etc.                                                        │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 2: For each listing, calculate percentile scores           │
│                                                                  │
│   For metric in [range, speed, altitude, ...]:                 │
│       percentile = (count(worse) / total) * 100                │
│                                                                  │
│   If lower_is_better (price, time):                            │
│       percentile = 100 - percentile                            │
│                                                                  │
│   Example:                                                      │
│     Listing A: range=2700 (best of 10) → 100%                 │
│     Listing B: range=2040 (5th of 10) → 50%                   │
│     Listing C: range=1550 (worst of 10) → 0%                  │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 3: Group scores into categories                            │
│                                                                  │
│   Performance = avg(range_score, speed_score, altitude_score)  │
│   Condition = avg(total_time_score, engine_time_score)         │
│   Cosmetic = avg(interior_year_score, paint_year_score)        │
│   Avionics = avionics_value_score                              │
│   Value = price_score                                          │
│                                                                  │
│   Example:                                                      │
│     Performance: (100 + 85 + 90) / 3 = 91.7                   │
│     Condition: (70 + 65) / 2 = 67.5                           │
│     Cosmetic: (80 + 85) / 2 = 82.5                            │
│     Avionics: 75                                               │
│     Value: 88                                                  │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 4: Calculate overall match score                           │
│                                                                  │
│   category_avg = (91.7 + 67.5 + 82.5 + 75 + 88) / 5 = 80.9   │
│                                                                  │
│   overall_match_score = (category_avg * 0.7) + (value * 0.3)  │
│                       = (80.9 * 0.7) + (88 * 0.3)             │
│                       = 56.6 + 26.4                            │
│                       = 83.0                                   │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 5: Generate top reasons                                    │
│                                                                  │
│   Sort categories by score:                                     │
│     1. Performance: 91.7 → "Excellent performance specs"       │
│     2. Value: 88.0 → "Outstanding value for price"            │
│     3. Cosmetic: 82.5 → "Recently updated interior/paint"     │
│                                                                  │
│   Return top 3 reasons                                         │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
Output: Ranked listings with match scores
```

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Security Layers                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Layer 1: Authentication                                        │
│    ├─ Password hashing (Werkzeug)                              │
│    ├─ Session management (Flask secure sessions)               │
│    └─ Login required decorator                                 │
│                                                                  │
│  Layer 2: Authorization                                         │
│    ├─ Admin-only routes (@admin_required)                      │
│    ├─ Owner-only edits (user_id check)                         │
│    └─ Server-side enforcement (no client trust)                │
│                                                                  │
│  Layer 3: Payment Security                                      │
│    ├─ Stripe webhook signature verification                    │
│    ├─ Subscription status tracking                             │
│    └─ Payment before listing goes pending                      │
│                                                                  │
│  Layer 4: Audit Trail                                           │
│    ├─ All admin actions logged                                 │
│    ├─ IP address tracking                                      │
│    └─ Immutable audit log                                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         GitHub Repo                              │
│                    (jet-finder)                                  │
│                                                                  │
│  ├─ app.py (1133 lines)                                        │
│  ├─ requirements.txt                                            │
│  ├─ Procfile                                                    │
│  ├─ runtime.txt                                                 │
│  ├─ seed_data.py                                                │
│  └─ frontend/dist/ (React build)                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Auto-deploy on push
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Railway Platform                            │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Web Service                                                │ │
│  │  ├─ Gunicorn (WSGI server)                                 │ │
│  │  ├─ Flask app (app.py)                                     │ │
│  │  └─ Port: 5015                                             │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                    │
│                              ▼                                    │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  PostgreSQL Service                                         │ │
│  │  ├─ Auto-provisioned                                        │ │
│  │  ├─ DATABASE_URL injected                                   │ │
│  │  └─ Persistent storage                                      │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  Environment Variables:                                          │
│    - SECRET_KEY                                                  │
│    - STRIPE_SECRET_KEY                                           │
│    - STRIPE_WEBHOOK_SECRET                                       │
│    - ADMIN_EMAIL                                                 │
│    - ADMIN_PASSWORD                                              │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Public URL
                              ▼
                    https://your-app.up.railway.app
```

## Module Organization in app.py

```
app.py (1133 lines)
│
├─ Lines 1-60: Configuration
│   ├─ Imports
│   ├─ Flask app setup
│   ├─ Environment variables
│   └─ Constants (plans, upload settings)
│
├─ Lines 61-180: Database
│   ├─ get_db_connection()
│   └─ init_db() - Schema creation
│
├─ Lines 181-240: Authentication & Authorization
│   ├─ @login_required decorator
│   ├─ @admin_required decorator
│   └─ log_audit_event()
│
├─ Lines 241-420: Match Scoring Engine
│   ├─ MatchScorer class
│   ├─ percentile_score()
│   ├─ calculate_match_scores()
│   └─ generate_top_reasons()
│
├─ Lines 421-530: Auth API Routes
│   ├─ POST /api/auth/register
│   ├─ POST /api/auth/login
│   ├─ POST /api/auth/logout
│   └─ GET /api/auth/me
│
├─ Lines 531-550: Profile API Routes
│   └─ GET /api/profiles
│
├─ Lines 551-750: Listing API Routes
│   ├─ GET /api/listings (with filters)
│   ├─ POST /api/listings (create)
│   └─ PUT /api/listings/<id> (update)
│
├─ Lines 751-900: Stripe API Routes
│   ├─ POST /api/listings/<id>/checkout
│   └─ POST /api/stripe/webhook
│
├─ Lines 901-1050: Admin API Routes
│   ├─ GET /api/admin/listings/pending
│   ├─ POST /api/admin/listings/<id>/approve
│   ├─ POST /api/admin/listings/<id>/reject
│   └─ GET /api/admin/audit
│
├─ Lines 1051-1100: Match Tool API Routes
│   └─ POST /api/match
│
└─ Lines 1101-1133: Frontend Serving & Main
    ├─ GET / (serve React)
    ├─ GET /<path> (SPA routing)
    └─ if __name__ == '__main__'
```

## Data Flow Summary

```
User Action → API Route → Authorization Check → Database Query/Update
                                                        ↓
                                                 Audit Logging
                                                        ↓
                                                  JSON Response
                                                        ↓
                                                   Frontend
```

## Key Design Decisions

1. **Single File Architecture**: All backend logic in `app.py` for simplicity
2. **PostgreSQL**: Railway-native database with proper relational schema
3. **Server-side Authorization**: No client-side trust, all checks in Flask
4. **Percentile Scoring**: Industry-standard, adaptive ranking
5. **Stripe Webhooks**: Reliable subscription management
6. **Audit Logging**: Complete trail of all admin actions
7. **Status-based Workflow**: Clear listing lifecycle (draft → pending → active)
8. **Single Origin**: Frontend and API on same domain (no CORS issues)
