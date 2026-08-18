# FluentStack — AI Technical English Tutor

FluentStack is a full-stack adaptive Technical English learning application for software professionals, especially backend developers. It combines a deterministic curriculum and learner state with real AI conversation and typed assessment.

The core design rule is: **AI controls the learning experience; the application controls truth and state.** LLM output is validated and only deterministic application services update mastery, placement, review schedules, and error memory.

## What works

- Email/password registration with Argon2 hashing, short-lived JWT access tokens, rotating HttpOnly refresh tokens, and refresh-family reuse detection
- Five-step professional onboarding
- Seven-dimension placement test with calibrated CEFR thresholds
- Persisted learner profile, skill states, weekly plan, mastery, and streak
- Personalized dashboard and a four-module B1 backend course with end-of-lesson error review
- Structured answer evaluation and persistent recurring-error aggregation
- Streaming Technical English tutor over SSE, with cancellation, retry, and safe typed UI blocks
- Technical vocabulary with collocations, examples, mistakes, search, and SM-2-inspired review state
- Mistakes, progress, weekly plan, documentation, interview, profile, and settings screens
- Knowledge ingestion endpoint and CLI with source/chunk metadata
- OpenAI Responses API for tutor conversation and typed free-answer evaluation; the mock provider is test-only and must be selected explicitly
- PostgreSQL/pgvector, Redis, Dramatiq worker, Alembic, Docker Compose, structured request logs

## Architecture

```text
frontend/                    React + Vite client
  src/api.ts                 REST and SSE client
  src/store.ts               UI/session state (Zustand)
  src/App.tsx                Routes and product surfaces

backend/app/
  api.py                     HTTP routes and transaction orchestration
  application.py             Use cases and deterministic state transitions
  evaluation.py              Typed AI evaluation and anti-keyword-stuffing policy
  tutor_service.py           Learner context, history, errors, vocabulary, and RAG assembly
  knowledge_service.py       UTF-8/Markdown/PDF extraction and chunking
  domain/learning.py         Personalization, mastery, SRS, placement algorithms
  curriculum.py              Deterministic skill graph, vocabulary, exercises
  ai/providers.py            LLM and embedding contracts + OpenAI/test providers
  ai/context.py              Token-bounded context selection
  models.py                  Relational learning-state model
  workers.py                 Durable Dramatiq embedding jobs
  cli/migrate.py             Schema bootstrap and Alembic upgrade entrypoint
  cli/ingest.py              Developer knowledge ingestion
```

SSE was selected for tutor streaming because the interaction is request/response with a single server-to-client token stream. It uses normal HTTP authentication, works through standard proxies, and gives the browser a direct cancellation path. WebSocket complexity is unnecessary until live duplex voice is introduced.

PostgreSQL with the pgvector extension is the deployment database. Knowledge chunks use a native `vector(1536)` column; the tutor first narrows candidates by cosine distance in PostgreSQL and then applies the portable metadata/lexical hybrid scorer. SQLite remains useful for isolated unit and API tests.

The unused LangGraph façade was removed. Placement and lesson workflows are ordinary application services because they are finite, transaction-heavy state machines; adding a graph framework there would add indirection without providing durable orchestration value.

## Local setup

Prerequisites: Python 3.12+ and Node 20+.

```bash
cp .env.example .env

cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev,quality]"
python -m app.cli.migrate
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

| Variable | Purpose | Default behavior |
| --- | --- | --- |
| `DATABASE_URL` | Async SQLAlchemy URL | local SQLite when omitted |
| `REDIS_URL` | Dramatiq/Redis URL | `redis://localhost:6379/0` |
| `SECRET_KEY` | JWT signing secret | development-only value |
| `ACCESS_TOKEN_MINUTES` | Session lifetime | `1440` |
| `REFRESH_TOKEN_DAYS` | Rotating refresh-session lifetime | `30` |
| `LLM_PROVIDER` | `openai` or explicit test-only `mock` | `openai` |
| `LLM_API_KEY` | Server-side provider credential | empty |
| `LLM_MODEL` | Task model | `gpt-5-mini` |
| `EMBEDDING_MODEL` | Embedding model name | `text-embedding-3-small` |
| `APP_ENV` | Runtime environment | `development` |
| `CORS_ORIGINS` | Allowed web origins | `http://localhost:5173` |
| `ADMIN_EMAILS` | Comma-separated emails allowed to ingest knowledge | empty |
| `VITE_API_URL` | Optional browser API base | `/api/v1` |

No credential is ever sent to the frontend.

## Real AI instead of mock

Set these server environment values and restart the backend:

```env
LLM_PROVIDER=openai
LLM_API_KEY=your-server-side-key
LLM_MODEL=gpt-5-mini
```

The application will then use the OpenAI Responses API implementation of `LLMProvider`. When `openai` is selected but the key is missing, the tutor returns a clear configuration error and never silently falls back to scripted replies. `MockLLMProvider` remains available only when `LLM_PROVIDER=mock` is explicitly selected for deterministic tests.

After recreating the backend container, verify a paid API call and reported token usage:

```powershell
.\scripts\openai-smoke.ps1
```

## Database, seed, and knowledge ingestion

The Docker backend applies managed migrations before serving traffic and seeds missing curriculum records idempotently. To prepare a local database:

```bash
cd backend
python -m app.cli.migrate
```

Ingest a UTF-8 text, Markdown, or text-based PDF source:

```bash
python -m app.cli.ingest path/to/material.md --type INTERNAL_CURRICULUM
```

The administrator-only `POST /api/v1/knowledge/ingest` endpoint accepts UTF-8 text, Markdown, and text-based PDFs. Scanned PDFs are rejected with an explicit OCR-required error. Accepted sources are queued in Redis, embedded by the worker, persisted in pgvector, and become available to tutor retrieval only after the job reaches `ready`.

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

Tests do not call a paid AI provider. They cover personalization, mastery, SRS, placement ordering, AI-evaluation policy, curriculum retries, vocabulary scoring, API authorization boundaries, duplicate accounts, rotating refresh tokens, knowledge parsing, and cross-user isolation. The acceptance script exercises the running Docker application; real tutor and free-answer acceptance requires a configured server-side OpenAI key.

## Current product boundaries

- Browser microphone, STT/TTS, and pronunciation scoring are not exposed; no inactive provider façade is presented as implemented.
- Text-based PDF extraction works. OCR and layout-aware table/figure reconstruction are not implemented.
- Email verification, password recovery, team administration, distributed rate limiting, and external telemetry exporters remain deployment/product work.

The UI labels unavailable voice functionality explicitly; the implemented learning, AI, vocabulary, progress, and retrieval paths persist real backend state.
