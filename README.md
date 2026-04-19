# Kiranaflow AI

Multi-modal credit intelligence system for kirana store analysis.

The platform accepts store images plus location data, runs a multi-stage analysis pipeline, and generates:
- Vision signals (shelf density, SKU diversity, category mix, estimated inventory)
- Geo signals (catchment, footfall proxy, competition)
- Fraud assessment flags
- Cash-flow estimates with confidence range
- Final recommendation and narrative summary

## Tech Stack

- Backend: FastAPI, SQLAlchemy, PostgreSQL
- Frontend: React + Vite + TypeScript
- Infra: Docker Compose
- CV/ML (optional in current setup): YOLO, CLIP, SAM, MiDaS

## Repository Structure

- backend: FastAPI app, pipeline services, models
- frontend: React app and dashboard UI
- docker-compose.yml: local multi-service orchestration
- implementation_plan.md: high-level implementation and assumptions

## Pipeline Flow

1. Submission ingestion (images + metadata + GPS)
2. Vision pipeline
3. Geo pipeline
4. Fraud checks
5. Fusion scoring (daily sales, monthly income, uncertainty)
6. Output generation (JSON + summary + recommendation)

Main orchestrator is in backend/app/services/pipeline_runner.py.

## Quick Start (Docker)

### Prerequisites

- Docker Desktop
- Git

### Run

```bash
docker compose up --build
```

Services:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs
- Postgres: localhost:5433

To run in detached mode:

```bash
docker compose up -d
```

To stop:

```bash
docker compose down
```

## Environment Variables

### Backend

Template: backend/.env.example

For local Docker, no external API keys are required.

Minimum useful defaults:
- DATABASE_URL (set by compose for backend container)
- STORAGE_BACKEND=local
- LOCAL_UPLOAD_DIR=uploads

Optional:
- AWS_BUCKET_NAME, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY

Geo stack:
- OpenStreetMap + Overpass API (no Google Maps key required)

### Frontend

File: frontend/.env

Required:
- VITE_API_URL=http://localhost:8000

## Current Runtime Behavior

This repo is currently configured for reliable local demo mode:
- Core backend/frontend/database are fully functional.
- If heavy ML packages are unavailable, the system uses fallbacks/mocks for some vision steps and still completes end-to-end.
- Geo services use free Overpass/OSM paths with fallback defaults on API timeout/rate limit.

## Common Commands

```bash
# service status
docker compose ps

# backend logs
docker compose logs backend --tail 200

# frontend logs
docker compose logs frontend --tail 200

# rerun pipeline for a submission from inside backend container
docker compose exec backend python -c "import asyncio; from app.services.pipeline_runner import run_full_pipeline; asyncio.run(run_full_pipeline('<submission-id>'))"
```

## API Notes

Base routes:
- GET /health
- GET /
- POST /api/v1/submissions
- GET /api/v1/submissions
- GET /api/v1/submissions/{submission_id}
- GET /api/v1/submissions/{submission_id}/status

Explore full schema and interactive testing at /docs.
