# JetSchoolUSA - Cloudflare Deployment

Modern aircraft marketplace built entirely on Cloudflare for global scale and low cost.

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│      Cloudflare Pages (Frontend)        │
│      React + Vite + Tailwind CSS        │
│      jetschoolusa.pages.dev             │
└────────────────┬────────────────────────┘
                 │ HTTPS
                 ▼
┌─────────────────────────────────────────┐
│    Cloudflare Workers (Backend API)     │
│    TypeScript + D1 Database + R2        │
│    jetschoolusa-api.nick-zahn777...     │
└────────────────┬────────────────────────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
┌─────────────┐    ┌─────────────┐
│   D1 DB     │    │  R2 Storage │
│ (SQLite)    │    │ (Media)     │
└─────────────┘    └─────────────┘
```

## 📁 Project Structure

```
jet-finder/
├── frontend/              # React frontend (Cloudflare Pages)
│   ├── src/              # React components & pages
│   ├── public/           # Static assets
│   ├── package.json
│   └── vite.config.js
│
├── worker-api/           # Cloudflare Worker backend
│   ├── src/              # TypeScript API routes
│   ├── migrations/       # D1 database migrations
│   ├── wrangler.toml     # Worker configuration
│   └── package.json
│
├── infra/                # Infrastructure scripts
│   ├── backup-d1.sh      # Database backup
│   └── smoke-tests.sh    # API tests
│
└── README.md
```

## 🚀 Deployment

### Frontend (Cloudflare Pages)

1. **Connect GitHub:**
   - Go to Cloudflare Dashboard → Workers & Pages → Pages
   - Create project → Connect to Git → GitHub
   - Select: `nzahn1560/jet-finder`

2. **Build Settings:**
   - Framework preset: `Vite`
   - Root directory: `frontend`
   - Build command: `npm ci && npm run build`
   - Build output directory: `dist`

3. **Environment Variables (Production):**
   ```
   VITE_API_URL=https://jetschoolusa-api.nick-zahn777.workers.dev
   VITE_SUPABASE_URL=https://thjvacmcpvwxdrfouymp.supabase.co
   VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ```

### Backend (Cloudflare Worker)

1. **Deploy Worker:**
   ```bash
   cd worker-api
   npm install
   npx wrangler deploy
   ```

2. **Database Setup:**
   ```bash
   cd worker-api
   npx wrangler d1 execute jetschoolusa-db --file=./migrations/0001_initial.sql --remote
   ```

## 🛠️ Local Development

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Backend Worker
```bash
cd worker-api
npm install
npx wrangler dev
```

## 📝 Tech Stack

- **Frontend:** React 18, Vite, Tailwind CSS, React Router, React Query
- **Backend:** Cloudflare Workers (TypeScript)
- **Database:** Cloudflare D1 (SQLite)
- **Storage:** Cloudflare R2 (Images/Videos)
- **Auth:** Supabase Authentication
- **Deployment:** Cloudflare Pages + Workers

## 🔐 Secrets

Never commit these files (already in .gitignore):
- `token.json`
- `credentials.json`
- `.env` files

## 📚 Documentation

- `CLOUDFLARE_PAGES_SETUP.md` - Frontend deployment guide
- `README_CLOUDFLARE.md` - Architecture overview
- `worker-api/wrangler.toml` - Worker configuration
