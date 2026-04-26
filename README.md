# 🤖 Order Supervisor POC

**AI-powered, long-running order supervision system.**  
One autonomous supervisor run per order — from creation to completion.

> An event-driven architecture where an AI agent monitors, reasons about, and takes action on orders over their entire lifecycle (hours, days, or weeks), waking and sleeping autonomously between events.

---

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [High-Level Architecture](#high-level-architecture)
- [Agent Tools (Business Actions)](#agent-tools-business-actions)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Option A — Docker Compose (Recommended)](#option-a--docker-compose-recommended)
  - [Option B — Manual Setup](#option-b--manual-setup)
  - [Access](#access)
- [API Reference](#api-reference)
- [Pre-Built Scenarios (Simulator)](#pre-built-scenarios-simulator)
- [Configuration](#configuration)
- [Features](#features)
- [License](#license)

---

## Overview

Order Supervisor is a proof-of-concept system that demonstrates how a **long-running AI agent** can autonomously manage the lifecycle of an e-commerce order. Unlike traditional request-response AI — where you ask a question and get an answer — this system:

1. **Persists** across hours/days with durable state stored in PostgreSQL.
2. **Sleeps** when there is nothing to do, conserving LLM compute.
3. **Wakes** when real-world events arrive (e.g. shipment delayed, payment failed) or on a self-determined schedule.
4. **Acts** by executing business actions such as messaging internal teams or contacting the customer.
5. **Learns** by updating its own internal state, instructions, and wake-up guidance dynamically.

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Next.js 16 (App Router) + Tailwind CSS v4 + MUI v9 | Dashboard, Run detail view, Event injection UI |
| **Backend** | Python 3.12 + FastAPI + SQLAlchemy (async) | REST API, Agent orchestration, Event processing |
| **Database** | PostgreSQL 16 | State persistence, Activity logs, Scheduler job store |
| **LLM** | Groq API (`llama-3.3-70b-versatile`) | Agent reasoning, Wake/Sleep classification, Final summaries |
| **Scheduling** | APScheduler (SQLAlchemy job store) | Durable delayed wake-ups that survive restarts |
| **Containerization** | Docker + Docker Compose | One-command local deployment |

---

## High-Level Architecture

```mermaid
graph TB
    subgraph "Frontend — Next.js"
        UI[Dashboard UI]
        RD[Run Detail Page]
        EI[Event Injection Panel]
    end

    subgraph "Backend — FastAPI"
        API[REST API Layer]
        CLS[Wake/Sleep Classifier]
        AGT[Agent Runtime Loop]
        TLS[Tool Executors]
        SCH[APScheduler]
    end

    subgraph "External"
        DB[(PostgreSQL)]
        LLM[Groq LLM API]
    end

    UI -->|HTTP| API
    RD -->|HTTP| API
    EI -->|POST /events| API

    API -->|Read/Write| DB
    API -->|Classify Event| CLS
    CLS -->|LLM Call| LLM

    API -->|Wake Agent| AGT
    AGT -->|LLM Reasoning + Tool Calls| LLM
    AGT -->|Execute Actions| TLS
    TLS -->|Log Activities| DB
    AGT -->|Update State| DB
    AGT -->|Schedule Wake| SCH
    SCH -->|Trigger at Time| AGT

    style UI fill:#1e293b,stroke:#3b82f6,color:#fff
    style RD fill:#1e293b,stroke:#3b82f6,color:#fff
    style EI fill:#1e293b,stroke:#3b82f6,color:#fff
    style API fill:#0f172a,stroke:#8b5cf6,color:#fff
    style CLS fill:#0f172a,stroke:#f59e0b,color:#fff
    style AGT fill:#0f172a,stroke:#10b981,color:#fff
    style TLS fill:#0f172a,stroke:#10b981,color:#fff
    style SCH fill:#0f172a,stroke:#f97316,color:#fff
    style DB fill:#1e1b4b,stroke:#6366f1,color:#fff
    style LLM fill:#1e1b4b,stroke:#ec4899,color:#fff
```

---

### Wake / Sleep Classifier

The classifier is a **lightweight LLM gate** that prevents unnecessary agent wake-ups, saving LLM compute costs.

```mermaid
flowchart TD
    E[Incoming Event] --> A{Event in ALWAYS_WAKE set?}
    A -->|Yes| W[✅ Wake Agent]
    A -->|No| B{Run is paused?}
    B -->|Yes| S[❌ Stay Asleep]
    B -->|No| C{Wake guidance exists?}
    C -->|No| W
    C -->|Yes| D[🤖 LLM Classifier Call]
    D -->|wake=true| W
    D -->|wake=false| S

    style W fill:#065f46,stroke:#10b981,color:#fff
    style S fill:#7f1d1d,stroke:#ef4444,color:#fff
    style D fill:#1e1b4b,stroke:#8b5cf6,color:#fff
```

**How it works:**
1. **Hard-coded overrides** — Critical events (`order_created`, `payment_failed`, `delivered`, `refund_requested`, `customer_message_received`) *always* wake the agent.
2. **Paused check** — If the run is paused by the user, the event is stored but the agent is not woken.
3. **LLM classification** — For borderline events, the classifier LLM receives the agent's `wake_guidance` (e.g., "Wake me for shipment delays, let me sleep through routine pings") and makes a fast yes/no decision.

---

### Agent Execution Loop

Once woken, the agent enters a **tool-calling loop** — it reasons about the situation and executes actions iteratively until it decides to sleep.

```mermaid
flowchart TD
    START[Agent Woken Up] --> LOAD[Load Run State + Supervisor + Last 30 Activities]
    LOAD --> PROMPT[Build System Prompt with state, history, instructions]
    PROMPT --> LLM[Send to Groq LLM]
    LLM --> TC{Tool calls in response?}
    TC -->|Yes| EXEC[Execute Tool: message_team / update_state / sleep / etc.]
    EXEC --> LOG[Log Activity to DB]
    LOG --> LLM
    TC -->|No| REASON[Record Final Reasoning]
    REASON --> CHECK{Completion recommended?}
    CHECK -->|Yes, order terminal| COMPLETE[Generate Final Summary → Complete Run]
    CHECK -->|No| SLEEP{Sleep was requested?}
    SLEEP -->|Yes| SCHEDULE[Schedule APScheduler Wake-Up Job]
    SLEEP -->|No| DEFAULT[Default Sleep: 30 min]
    DEFAULT --> SCHEDULE

    style START fill:#1e1b4b,stroke:#8b5cf6,color:#fff
    style LLM fill:#1e1b4b,stroke:#ec4899,color:#fff
    style COMPLETE fill:#065f46,stroke:#10b981,color:#fff
    style SCHEDULE fill:#78350f,stroke:#f59e0b,color:#fff
```

**Key details:**
- **Max 10 iterations** per wake cycle to prevent runaway loops.
- The agent's system prompt includes: current state JSON, additional instructions, last 30 activities, the wake trigger, and available actions.
- Every tool execution is logged as an `Activity` record in PostgreSQL.
- The agent can **dynamically update its own wake guidance** via the `set_wake_guidance` tool, affecting future classifier decisions.

---

### Scheduled Wake-Ups

When the agent decides to sleep, it schedules a future wake-up using APScheduler with a **durable SQLAlchemy job store** (survives server restarts).

```mermaid
sequenceDiagram
    participant AGT as Agent Runtime
    participant DB as PostgreSQL
    participant SCH as APScheduler

    AGT->>DB: Set run.status = "sleeping", run.next_wake_at = T+30min
    AGT->>SCH: schedule_wake_up(run_id, wake_at)
    SCH->>DB: Store scheduled job (SQLAlchemy job store)

    Note over SCH: ⏳ Time passes...

    SCH->>AGT: DateTrigger fires → _wake_run(run_id)
    AGT->>DB: Load run, set status = "running"
    AGT->>AGT: Execute agent cycle (same loop as above)
```

**Additionally:**
- A **periodic job** (`check_expired_runs`) runs every 5 minutes to auto-complete any runs that have exceeded their `max_end_at` (default: 72 hours).
- Past-due wake times are handled immediately rather than being silently dropped.
- If the agent doesn't explicitly call `sleep_until`, a **default 30-minute** wake interval is applied.

--

Users can also **manually terminate** a run via `POST /api/runs/{id}/terminate`, which generates a final summary regardless of order status.

---

## Agent Tools (Business Actions)

The agent can call these tools during its reasoning loop. Tools are filtered per-supervisor based on `available_actions`.

| Tool | Type | Description |
|------|------|-------------|
| `message_fulfillment_team` | Business Action | Send a message (with priority) to the fulfillment team |
| `message_payments_team` | Business Action | Send a message (with priority) to the payments team |
| `message_logistics_team` | Business Action | Send a message (with priority) to the logistics team |
| `message_customer` | Business Action | Send a message to the customer (with subject line) |
| `create_internal_note` | Business Action | Create an internal note (observation, risk, decision, escalation, general) |
| `sleep_until` | Runtime | Schedule sleep for N minutes or until a specific time |
| `update_state` | Runtime | Merge key-value updates into the run's persistent state |
| `set_wake_guidance` | Runtime | Update instructions for the wake/sleep classifier |
| `recommend_completion` | Runtime | Recommend the run should be completed (system verifies against terminal statuses) |

> **Runtime tools** (`sleep_until`, `update_state`, `set_wake_guidance`, `recommend_completion`) are always available regardless of supervisor configuration.

---

## Project Structure

```
order-supervisor-poc/
├── docker-compose.yml              # One-command deployment (Postgres + Backend + Frontend)
├── .env                             # Environment variables (GROQ_API_KEY, DB URLs)
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt             # Python dependencies
│   ├── alembic.ini                  # Alembic migration config
│   ├── alembic/                     # Database migration scripts
│   └── app/
│       ├── main.py                  # FastAPI app entry point + lifespan (scheduler init)
│       ├── config.py                # Pydantic Settings (env vars → typed config)
│       ├── database.py              # Async SQLAlchemy engine + session factory
│       ├── models.py                # ORM models: Supervisor, Run, Activity
│       ├── schemas.py               # Pydantic request/response schemas
│       ├── scheduler.py             # APScheduler: schedule/cancel wake-ups, expired run checks
│       ├── api/
│       │   ├── supervisors.py       # CRUD for supervisor configs + default seeding
│       │   ├── runs.py              # Run lifecycle: create, list, pause, resume, terminate
│       │   └── events.py            # Event injection, wake/sleep routing, scenario simulator
│       └── agent/
│           ├── classifier.py        # Lightweight LLM classifier (wake vs. stay asleep)
│           ├── runtime.py           # Main agent loop: LLM reasoning + tool-calling cycle
│           ├── tools.py             # Tool definitions (OpenAI function schema) + executors
│           └── prompts.py           # System prompt templates for agent, classifier, final summary
│
└── frontend/
    ├── Dockerfile
    ├── package.json                 # Next.js 16 + MUI + Tailwind
    └── src/
        ├── lib/
        │   └── api.ts               # API client (fetch wrapper for all backend endpoints)
        └── app/
            ├── layout.tsx            # Root layout with sidebar navigation
            ├── page.tsx              # Dashboard page (stats + recent runs)
            ├── globals.css           # Global styles
            ├── runs/
            │   ├── page.tsx          # Runs list page
            │   └── [id]/            # Run detail page (activities, event injection, controls)
            └── supervisors/
                └── page.tsx          # Supervisor management page
```

---

## Getting Started

### Prerequisites

- **Docker & Docker Compose** (for containerized setup)
- **Groq API Key** — get one free at [console.groq.com](https://console.groq.com)
- For manual setup: Python 3.12+, Node.js 20+, PostgreSQL 16

### Option A — Docker Compose (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/ankurraj2003/order-supervisor-poc.git
cd order-supervisor-poc

# 2. Set your Groq API key in the .env file (or export it)
echo "GROQ_API_KEY=gsk_your-key-here" > .env

# 3. Start all services (PostgreSQL + Backend + Frontend)
docker compose up --build
```

This will:
- Start PostgreSQL on port `5432`
- Run Alembic migrations automatically
- Start the FastAPI backend on port `8000`
- Start the Next.js frontend on port `3000`

### Option B — Manual Setup

#### 1. Start PostgreSQL

```bash
docker run -d --name order-supervisor-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=order_supervisor \
  -p 5432:5432 \
  postgres:16-alpine
```

#### 2. Start the Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv

# Windows
.\.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
echo "GROQ_API_KEY=gsk_your-key-here" > .env

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --port 8000
```

#### 3. Start the Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

### Access

| Service | URL |
|---------|-----|
| **Frontend Dashboard** | [http://localhost:3000](http://localhost:3000) |
| **Backend API** | [http://localhost:8000](http://localhost:8000) |
| **Interactive API Docs (Swagger)** | [http://localhost:8000/docs](http://localhost:8000/docs) |
| **Health Check** | [http://localhost:8000/api/health](http://localhost:8000/api/health) |

---

## API Reference

### Supervisors

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/supervisors` | List all supervisor configs (auto-seeds defaults if empty) |
| `GET` | `/api/supervisors/{id}` | Get a supervisor by ID |
| `POST` | `/api/supervisors` | Create a new supervisor config |
| `PUT` | `/api/supervisors/{id}` | Update an existing supervisor |

### Runs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/runs` | Create and start a new run for an order |
| `GET` | `/api/runs` | List all runs (optionally filter by `?status=sleeping`) |
| `GET` | `/api/runs/stats` | Get dashboard statistics (total, active, completed, events, actions) |
| `GET` | `/api/runs/{id}` | Get full run details (state, supervisor, instructions, etc.) |
| `GET` | `/api/runs/{id}/activities` | Get activity log (supports `?limit=`, `?offset=`, `?activity_type=`) |
| `POST` | `/api/runs/{id}/instructions` | Add a run-specific instruction to the agent's context |
| `POST` | `/api/runs/{id}/pause` | Pause a run (cancels scheduled wake-ups) |
| `POST` | `/api/runs/{id}/resume` | Resume a paused run (triggers immediate agent evaluation) |
| `POST` | `/api/runs/{id}/terminate` | Terminate a run and generate a final summary |

### Events

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/runs/{id}/events` | Inject an event into a run |
| `POST` | `/api/simulator/scenario?run_id={id}` | Fire a pre-built event scenario |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |

---

## Pre-Built Scenarios (Simulator)

The simulator lets you fire a sequence of events into a run to test different order journeys. Events are fired with a 3-second delay between each.

| Scenario | Events Sequence |
|----------|----------------|
| **`happy_path`** | `order_created` → `payment_confirmed` → `shipment_created` → `delivered` |
| **`delayed_shipment`** | `order_created` → `payment_confirmed` → `shipment_created` → `shipment_delayed` → `customer_message_received` → `delivered` |
| **`payment_failure`** | `order_created` → `payment_failed` → `customer_message_received` → `payment_confirmed` → `shipment_created` → `delivered` |
| **`refund`** | `order_created` → `payment_confirmed` → `shipment_created` → `delivered` → `refund_requested` |

---

## Configuration

All configuration is managed via environment variables (loaded from `.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/order_supervisor` | Async PostgreSQL connection string |
| `DATABASE_URL_SYNC` | `postgresql+psycopg2://postgres:postgres@localhost:5432/order_supervisor` | Sync PostgreSQL connection (for APScheduler job store) |
| `GROQ_API_KEY` | — | **Required.** Your Groq API key |
| `AGENT_MODEL` | `llama-3.3-70b-versatile` | LLM model for the main agent reasoning |
| `CLASSIFIER_MODEL` | `llama-3.3-70b-versatile` | LLM model for the wake/sleep classifier |
| `MAX_RUN_AGE_HOURS` | `72` | Auto-complete runs older than this |
| `DEFAULT_WAKE_INTERVAL_MINUTES` | `30` | Default sleep duration when agent doesn't explicitly set one |

---

## Features

- ✅ **Long-running AI agent per order** — persistent state across wake/sleep cycles
- ✅ **Event-driven wake/sleep** — intelligent classifier gates agent wake-ups
- ✅ **Scheduled wake-ups** — durable APScheduler jobs stored in PostgreSQL
- ✅ **5 business actions** — message teams (fulfillment, payments, logistics), message customer, internal notes
- ✅ **4 runtime tools** — sleep control, state management, wake guidance, completion recommendation
- ✅ **Activity timeline** — full audit trail of events, decisions, actions, and reasoning
- ✅ **Dynamic instructions** — add run-specific instructions to the agent at any time
- ✅ **Agent-generated wake guidance** — the agent teaches the classifier when to wake it
- ✅ **Pre-built event scenarios** — one-click simulation of common order journeys
- ✅ **Pause / Resume / Terminate** — full lifecycle controls for every run
- ✅ **LLM-generated final summary** — actions taken, key learnings, and recommendations
- ✅ **Multiple supervisor templates** — different personality/aggressiveness profiles
- ✅ **Auto-expiry** — runs older than 72 hours are automatically completed
- ✅ **Full REST API** — with interactive Swagger docs at `/docs`

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
