# FluentStack — AI Technical English Tutor

FluentStack is a working full-stack MVP for adaptive Technical English practice. It is built for software professionals—especially backend developers—and combines a deterministic curriculum and learner state with an AI tutor that controls the presentation, conversation, and feedback.

The core design rule is: **AI controls the learning experience; the application controls truth and state.** LLM output is validated and only deterministic application services update mastery, placement, review schedules, and error memory.

## What works

- Email/password registration with Argon2 hashing and JWT sessions
- Five-step professional onboarding
- Seven-dimension placement test with calibrated CEFR thresholds
- Persisted learner profile, skill states, weekly plan, mastery, and streak
- Personalized dashboard and a four-module B1 backend course with end-of-lesson error review
- Structured answer evaluation and persistent recurring-error aggregation
- Streaming Technical English tutor over SSE, with cancellation, retry, and safe typed UI blocks
- Technical vocabulary with collocations, examples, mistakes, search, and SM-2-inspired review state
- Mistakes, progress, weekly plan, documentation, interview, profile, and settings screens
- Knowledge ingestion endpoint and CLI with source/chunk metadata
- Mock AI by default; OpenAI Responses API provider behind an abstraction
- PostgreSQL/pgvector, Redis, Dramatiq worker, Alembic, Docker Compose, structured request logs

## Architecture

```text
frontend/                    React + Vite client
  src/api.ts                 REST and SSE client
  src/store.ts               UI/session state (Zustand)
  src/App.tsx                Routes and product surfaces

backend/app/
  api.py                     HTTP transport only
  application.py             Use cases and deterministic state transitions
  domain/learning.py         Personalization, mastery, SRS, placement algorithms
  curriculum.py              Deterministic skill graph, vocabulary, exercises
  ai/providers.py            LLM/embedding/STT/TTS contracts + mock/OpenAI
  ai/context.py              Token-bounded context selection
  models.py                  Relational learning-state model
  workers.py                 Dramatiq background boundaries
  cli/ingest.py              Developer knowledge ingestion
```

SSE was selected for tutor streaming because the interaction is request/response with a single server-to-client token stream. It uses normal HTTP authentication, works through standard proxies, and gives the browser a direct cancellation path. WebSocket complexity is unnecessary until live duplex voice is introduced.

PostgreSQL is the production database. The default local configuration uses async SQLite so the complete demo starts without infrastructure; Docker always uses PostgreSQL. The knowledge schema keeps embeddings provider-agnostic as JSON for the demo. The migration path to a native `vector` column and hybrid `tsvector + vector` ranking is isolated to the RAG repository layer.

LangGraph is an integration boundary rather than the whole backend. Placement, Tutor, Lesson, and Planner workflows have deterministic application services today; provider/state nodes can be introduced without moving persistence authority into the graph.

## Local setup

Prerequisites: Python 3.12+ and Node 20+.

```bash
cp .env.example .env

cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev,quality]"
uvicorn app.main:app --reload

# second terminal
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. API docs are at `http://localhost:8000/api/docs`.

## Docker

Copy `.env.example` to `.env` and set a non-default `SECRET_KEY`, then run:

```bash
docker compose up --build
```

The application is served at `http://localhost:5173`; the Docker API is at `http://localhost:8001` (container port `8000`).

## Environment variables

| Variable | Purpose | Default/demo behavior |
| --- | --- | --- |
| `DATABASE_URL` | Async SQLAlchemy URL | local SQLite when omitted |
| `REDIS_URL` | Dramatiq/Redis URL | `redis://localhost:6379/0` |
| `SECRET_KEY` | JWT signing secret | development-only value |
| `ACCESS_TOKEN_MINUTES` | Session lifetime | `1440` |
| `LLM_PROVIDER` | `mock` or `openai` | `mock` |
| `LLM_API_KEY` | Server-side provider credential | empty |
| `LLM_MODEL` | Task model | `gpt-5-mini` |
| `EMBEDDING_MODEL` | Embedding model name | `text-embedding-3-small` |
| `APP_ENV` | Runtime environment | `development` |
| `CORS_ORIGINS` | Allowed web origins | `http://localhost:5173` |
| `VITE_API_URL` | Optional browser API base | `/api/v1` |

No credential is ever sent to the frontend.

## Real AI instead of mock

Set these server environment values and restart the backend:

```env
LLM_PROVIDER=openai
LLM_API_KEY=your-server-side-key
LLM_MODEL=gpt-5-mini
```

The application will then use the OpenAI Responses API implementation of `LLMProvider`. `MockLLMProvider` remains available for deterministic tests and offline demos.

## Database, seed, and knowledge ingestion

The backend creates and seeds a fresh demo database on first startup. For managed schema changes:

```bash
cd backend
alembic upgrade head
```

Ingest a UTF-8 text or Markdown source:

```bash
python -m app.cli.ingest path/to/material.md --type INTERNAL_CURRICULUM
```

The authenticated `POST /api/v1/knowledge/ingest` endpoint supports the same developer/admin flow. PDF parsing is represented by the installed `pypdf` dependency and is the next ingestion adapter; text/Markdown ingestion is active now.

## Validation

```bash
cd backend
pip install -e ".[dev,quality]"
pytest -q
ruff check .
mypy app

cd ../frontend
npm run build

cd ..
powershell -File scripts/acceptance.ps1
```

Tests do not call a paid AI provider. They cover personalization priority, prerequisite readiness, mastery updates, SRS scheduling, placement calibration, tutor context, curriculum retries, and vocabulary scoring. The acceptance script creates a fresh learner through the running Docker application, completes the full B1 course through correct and incorrect branches, checks progress, reviews vocabulary, and holds a multi-turn tutor conversation.

## Deliberately deferred

- Browser microphone, STT/TTS, and pronunciation scoring (interfaces exist; UI correctly marks voice unavailable)
- Native pgvector embeddings and production hybrid ranking adapter
- Automated PDF layout-aware parsing and curated-knowledge extraction
- Refresh-token rotation, email verification, password recovery, and team accounts
- Full production rate-limiter storage and hosted observability exporters
- Production-grade LangGraph checkpoints for long-running placement/lesson graphs

These are extension points, not decorative features in the current UI.
