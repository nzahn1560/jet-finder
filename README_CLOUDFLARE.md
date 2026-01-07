# Jet Finder - Cloudflare Architecture

Complete serverless architecture built on Cloudflare for scale and low cost.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Cloudflare Pages                     │
│              (React + Tailwind Frontend)                │
│                   jetschoolusa.com                      │
└────────────────────────┬────────────────────────────────┘
                         │
                         │ HTTPS
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  Cloudflare Workers                     │
│              (REST API + Auth + Media)                  │
│            jetfinder-api.workers.dev                    │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ Listings │  │   Auth   │  │  Upload  │             │
│  │   API    │  │   API    │  │   API    │             │
│  └──────────┘  └──────────┘  └──────────┘             │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │  Admin   │  │  Tools   │  │  Usage   │             │
│  │   API    │  │   API    │  │Tracking  │             │
│  └──────────┘  └──────────┘  └──────────┘             │
└──────────┬──────────────┬──────────────┬───────────────┘
           │              │              │
           ▼              ▼              ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐
    │   D1 DB  │  │R2 Images │  │R2 Videos │
    │(SQLite)  │  │   Bucket │  │  Bucket  │
    └──────────┘  └──────────┘  └──────────┘
           │
           ▼
    ┌──────────┐
    │ Supabase │
    │   Auth   │
    └──────────┘
```

## Tech Stack

### Frontend
- **React 18** + **Vite** - Modern React app
- **Tailwind CSS** - Utility-first styling
- **React Router** - Client-side routing
- **React Query** - Data fetching & caching
- **Supabase Auth** - Authentication

### Backend
- **Cloudflare Workers** - Serverless API (TypeScript)
- **D1 Database** - SQLite-based edge database
- **R2 Storage** - Object storage for media
- **KV Namespace** - Edge caching
- **Supabase Auth** - User authentication

## Features

✅ **User Authentication**
- Sign up, login, password reset
- JWT-based session management
- User profile sync to D1

✅ **Listings Management**
- Create, edit, delete listings
- Status workflow: pending → approved → active
- Search and filter
- 25 images + 1 video per listing

✅ **Media Optimization**
- Automatic image resizing
- WebP conversion
- Multiple size variants (thumbnail, medium, large)
- Video compression (via R2)

✅ **Admin Dashboard**
- Approve/reject listings
- User management
- Usage analytics

✅ **Internal Tools**
- Built-in aircraft matching/scoring tools
- Usage tracking per user
- 15 uses/month per user average

✅ **Scalability**
- Auto-scales to 500k+ users/month
- Edge computing for low latency
- CDN for static assets

## Project Structure

```
jet-finder/
├── workers/                 # Cloudflare Workers backend
│   ├── src/
│   │   ├── index.ts        # Main worker entry
│   │   ├── routes/         # API route handlers
│   │   │   ├── listings.ts
│   │   │   ├── auth.ts
│   │   │   ├── upload.ts
│   │   │   ├── admin.ts
│   │   │   ├── tools.ts
│   │   │   └── usage.ts
│   │   └── utils/          # Helper functions
│   │       ├── auth.ts     # Supabase auth
│   │       ├── db.ts       # D1 helpers
│   │       ├── media.ts    # Media optimization
│   │       └── response.ts # HTTP helpers
│   ├── migrations/         # D1 database migrations
│   ├── wrangler.toml       # Workers config
│   └── package.json
│
├── frontend/               # React frontend
│   ├── src/
│   │   ├── pages/         # Page components
│   │   ├── components/    # Reusable components
│   │   └── lib/           # Utilities
│   │       └── supabase-auth.js
│   ├── package.json
│   └── vite.config.js
│
└── DEPLOYMENT.md          # Step-by-step deployment guide
```

## Quick Start

1. **Clone and install**:
```bash
git clone <repo>
cd jet-finder

# Install backend dependencies
cd workers && npm install

# Install frontend dependencies
cd ../frontend && npm install
```

2. **Set up Supabase**:
   - Create project at supabase.com
   - Get API keys
   - Configure auth redirect URLs

3. **Set up Cloudflare**:
   - Create D1 database
   - Create R2 buckets
   - Create KV namespace

4. **Configure environment**:
   - Copy `.env.example` files
   - Fill in Supabase and Cloudflare credentials

5. **Run migrations**:
```bash
cd workers
wrangler d1 migrations apply jetfinder-db --local  # Local
wrangler d1 migrations apply jetfinder-db          # Production
```

6. **Deploy**:
```bash
# Deploy backend
cd workers && npm run deploy

# Deploy frontend (via Cloudflare Pages dashboard or CLI)
cd frontend && npm run build
npx wrangler pages deploy dist
```

## Cost Breakdown

### MVP (0-10k users/month)
- Cloudflare Free Plan: $0
- Supabase Free Plan: $0
- **Total: $0/month**

### Growing (10k-100k users/month)
- Cloudflare Workers: $5/month
- D1: $10/month
- R2: $5/month
- Supabase Pro: $25/month
- **Total: ~$45/month**

### Scale (100k-500k users/month)
- Cloudflare Workers: $10/month
- D1: $25/month
- R2: $15/month
- Supabase Pro: $25/month
- Bandwidth: Included
- **Total: ~$75-100/month**

**Actual costs depend on usage patterns!**

## API Endpoints

### Listings
- `GET /api/listings` - List all active listings
- `GET /api/listings/:id` - Get single listing
- `POST /api/listings` - Create listing (auth required)
- `PUT /api/listings/:id` - Update listing (owner only)
- `DELETE /api/listings/:id` - Delete listing (owner only)

### Auth
- `GET /api/auth/me` - Get current user (auth required)
- `POST /api/auth/sync` - Sync Supabase user to D1

### Upload
- `POST /api/upload/image` - Upload image (auth required)
- `POST /api/upload/video` - Upload video (auth required)
- `DELETE /api/upload/image/:key` - Delete image (owner only)

### Admin
- `GET /api/admin/listings` - List pending listings (admin only)
- `POST /api/admin/listings/:id/approve` - Approve listing (admin only)
- `POST /api/admin/listings/:id/reject` - Reject listing (admin only)

### Tools
- `POST /api/tools/:toolName` - Use internal tool (auth required)

### Usage
- `GET /api/usage/me` - Get user's usage stats (auth required)
- `GET /api/usage/all` - Get all usage stats (admin only)

## Database Schema

See `workers/migrations/0001_initial.sql` for complete schema.

Key tables:
- `users` - User metadata (synced from Supabase)
- `listings` - Aircraft listings
- `listing_images` - Image URLs and metadata
- `performance_profiles` - Aircraft specifications
- `usage_tracking` - Tool usage analytics
- `approvals` - Admin approval history

## Media Storage

### Images
- Stored in R2 bucket: `jetfinder-images`
- Automatic optimization: WebP conversion, resizing
- Variants: thumbnail (300x300), medium (800x800), large (1920x1920)
- Max size: 2MB per image
- 25 images per listing

### Videos
- Stored in R2 bucket: `jetfinder-videos`
- Max size: 100MB (compresses to ~60MB)
- 1 video per listing

## Monitoring

- **Cloudflare Analytics**: Built-in metrics
- **Workers Logs**: `wrangler tail`
- **D1 Queries**: Monitor in dashboard
- **R2 Usage**: Track storage and operations

## Support

- 📖 [Deployment Guide](./DEPLOYMENT.md) - Complete setup instructions
- 🔧 [Cloudflare Docs](https://developers.cloudflare.com/)
- 🔐 [Supabase Docs](https://supabase.com/docs)

