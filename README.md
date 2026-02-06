# AppAdvice System

AI-powered iOS app discovery platform with real-time price tracking, semantic recommendations, and personalized alerts.

## The Full Trio Architecture

### 🔄 Data Freshness
- **Scheduled Scrapers**: APScheduler runs every 15 minutes
- **Price History**: Time-series tracking with change detection
- **Real-time Notifications**: WebSocket + Email alerts

### 🤖 AI Recommendations
- **Pinecone Vector DB**: Semantic search on app descriptions
- **Embeddings**: OpenAI text-embedding-3-small
- **Hybrid Search**: Dense vectors + metadata filtering

### 💰 Monetization
- **Affiliate Links**: App Store affiliate program
- **Premium Tier**: Price alerts, advanced filters, API access
- **B2B API**: Sell data to other platforms

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15 (App Router), Tailwind, shadcn/ui |
| Backend | FastAPI, SQLAlchemy 2.0, Pydantic v2 |
| Database | PostgreSQL (Neon), Redis (Upstash) |
| Vector DB | Pinecone |
| Embeddings | OpenAI API |
| Scraping | Playwright, aiohttp |
| Deployment | Vercel (frontend), Railway/Render (backend) |

## Project Structure

```
app-advice-system/
├── frontend/          # Next.js 15 App Router
├── backend/           # FastAPI + async scrapers
├── shared/            # Type definitions, schemas
└── scripts/           # Deployment & utility scripts
```

## Quick Start

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

## Environment Variables

Copy `.env.example` to `.env` and fill in:
- `DATABASE_URL` - PostgreSQL connection
- `PINECONE_API_KEY` - Vector database
- `OPENAI_API_KEY` - Embeddings
- `REDIS_URL` - Caching & queues

## License

MIT
