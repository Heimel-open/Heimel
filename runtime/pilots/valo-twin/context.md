# VALO Twin v2.0 — Context

## Product
VALO Twin — LinkedIn AI agent for Njål Gaute Solland

## Repo
nsolland/Valo-Twin → deploys to separate Vercel project

## Tech Stack
- Frontend: React 19 + TypeScript + Tailwind + shadcn/ui
- Backend: Hono + tRPC + Drizzle ORM
- Database: MySQL (PlanetScale/Railway/any host)
- AI: Gemini 2.0 Flash
- Gate: 8 VALO instruments

## Environment Variables (Vercel)
| Variable | Required | Source |
|----------|----------|--------|
| GEMINI_API_KEY | YES | aistudio.google.com |
| DATABASE_URL | YES | PlanetScale or Railway MySQL |

## Deploy Steps
1. Vercel Dashboard → Add New Project
2. Import: nsolland/Valo-Twin
3. Framework: Other
4. Root Directory: ./
5. Build Command: npm run build
6. Output Directory: dist
7. Add Environment Variables (above)
8. Deploy

## Database Setup
```bash
npm run db:push
```

## Pages
| Route | Purpose |
|-------|---------|
| / | Dashboard with stats and activity |
| /draft | Paste LinkedIn content, generate reply with VALO gate |
| /queue | Approve/reject/post drafts |
| /watchlist | Track contacts with flags |

## Features
- Draft generator (reply/dm/post/analyze/redteam modes)
- Creative Mode toggle
- VALO 8-instrument gate with VU-meter
- Approval queue (persistent in MySQL)
- Watchlist with 4 flags (monitor/engage/avoid/critical)
- Activity log (WORM-style audit)

## Status
Built: 2025-06-13
Pushed: YES (commit d3769b5)
Deployed: Needs Vercel setup

## Priority Order
1. Set GEMINI_API_KEY
2. Set DATABASE_URL  
3. npm run db:push
4. Deploy
5. Test /draft page
