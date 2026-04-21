# Order Supervisor POC

AI-powered long-running order supervision system. One supervisor run per order, from creation to completion.

## Architecture

- **Frontend**: Next.js 15 (App Router) + Tailwind CSS v4
- **Backend**: Python FastAPI + SQLAlchemy (async)
- **Database**: PostgreSQL
- **LLM**: Groq (llama-3.3-70b-versatile)
- **Scheduling**: APScheduler (SQLAlchemy job store)

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Groq API Key

### 1. Start with Docker Compose

```bash
# Set your Groq API key
export GROQ_API_KEY=gsk_your-key-here

# Start all services
docker compose up --build
```

### 2. Manual Setup

#### PostgreSQL
```bash
# Start PostgreSQL (Docker)
docker run -d --name order-supervisor-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=order_supervisor \
  -p 5432:5432 \
  postgres:16-alpine
```

#### Backend
```bash
cd backend
pip install -r requirements.txt

# Copy and edit .env
cp ../.env.example .env
# Edit .env with your GROQ_API_KEY

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --port 8000
```

#### Frontend
```bash
cd frontend
npm install

# Start dev server
npm run dev
```

### 3. Access
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Features

- ✅ Long-running AI run per order
- ✅ Event-driven wake/sleep behavior
- ✅ Scheduled wake-ups via APScheduler
- ✅ Lightweight LLM classifier for event importance
- ✅ 5 business actions (message teams, create notes)
- ✅ Activity timeline with all actions/events/reasoning
- ✅ State/memory persistence across wake cycles
- ✅ Run-specific instructions (add anytime)
- ✅ Event injection UI + pre-built scenarios
- ✅ Pause / Resume / Terminate controls
- ✅ Final summary with learnings and recommendations
- ✅ Multiple supervisor templates
- ✅ Agent-generated wake-up guidance

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/supervisors | Create supervisor config |
| GET | /api/supervisors | List supervisors |
| GET | /api/supervisors/{id} | Get supervisor |
| PUT | /api/supervisors/{id} | Update supervisor |
| POST | /api/runs | Start a new run |
| GET | /api/runs | List runs |
| GET | /api/runs/stats | Dashboard stats |
| GET | /api/runs/{id} | Get run detail |
| GET | /api/runs/{id}/activities | Get activity log |
| POST | /api/runs/{id}/events | Inject event |
| POST | /api/runs/{id}/instructions | Add instruction |
| POST | /api/runs/{id}/pause | Pause run |
| POST | /api/runs/{id}/resume | Resume run |
| POST | /api/runs/{id}/terminate | Terminate run |
| POST | /api/simulator/scenario | Fire event scenario |