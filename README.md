# Air Quality Web GIS (Environmental Engineering Portfolio)

Production-minded air quality platform for environmental monitoring, compliance screening, and atmospheric dispersion visualization.

## Why This Project Stands Out
- Domain-focused engineering: ISPU computation, ambient standard checks, and dispersion mapping in one product.
- Full-stack implementation: FastAPI backend + spatial front-end visualization.
- Security-aware delivery: environment-based secrets and configurable CORS policy.
- Testable core logic: unit and API tests for critical calculations and service health.

## Core Capabilities
- ISPU engine (PermenLHK No. 14/2020 style breakpoint interpolation).
- Compliance checks against:
  - Indonesia PP No. 22/2021 (ambient limits used in this prototype).
  - WHO 2021 Air Quality Guidelines (reference comparison layer).
- Monitoring dashboard data feed for NTB station scenarios.
- OpenAir-style analytics:
  - Wind rose
  - Polar plot
  - Pollutant time series
- AERMOD-style and CALPUFF-style visualization simulators for plume behavior insights.

## Architecture
- Backend: FastAPI, NumPy/SciPy, SQLAlchemy/PostGIS-ready models.
- Frontend: HTML/CSS/JavaScript with map + chart modules.
- Infra: Docker Compose with PostGIS, Redis, optional Celery worker.

## Scientific and Compliance Boundaries
This repository is an engineering portfolio prototype.
- It uses a local synthetic telemetry generator for repeatable demos.
- AERMOD/CALPUFF modules are simplified educational simulators, not replacement for certified regulatory modeling workflows.
- Compliance outputs are screening indicators and must be validated in formal EIA/AMDAL or permitting processes.

See:
- `docs/SCIENTIFIC_BOUNDARIES.md`
- `docs/COMPLIANCE_SCOPE.md`
- `docs/SECURITY_AND_PRIVACY.md`

## Quick Start (Local)
1. Create env file:
   - Copy `.env.example` to `.env`
   - Replace placeholders for `SECRET_KEY` and database password.
2. Install backend dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
3. Run API server:
   ```bash
   uvicorn main:app --reload
   ```
4. Open dashboard:
   - [http://127.0.0.1:8000/app/](http://127.0.0.1:8000/app/)

## Docker
```bash
docker compose --env-file .env up --build
```

## Testing
```bash
cd backend
pytest -q
```

## API Health Check
- `GET /api/health`

## Portfolio Notes for Recruiters
- Prioritizes practical environmental analytics with clear system boundaries.
- Demonstrates ability to connect scientific logic, data services, and geospatial visualization.
- Includes baseline secure configuration practices expected in real deployments.
