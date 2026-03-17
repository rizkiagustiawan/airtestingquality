# Air Quality Web GIS (Environmental Engineering Portfolio)

Production-minded air quality platform for environmental monitoring, compliance screening, and atmospheric dispersion visualization.

## Try It Fast
- Public-safe default: the frontend loads the deterministic `synthetic` dataset first, so anyone can try the app without a WAQI token.
- Fastest Windows path:
  1. Open PowerShell in the repo root.
  2. Run `cd backend`
  3. Run `python -m venv .venv`
  4. Run `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`
  5. Go back to the repo root and run `run_dashboard.bat`
- Manual backend start:
  - `cd backend`
  - `.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000`
- Optional real-data mode:
  - add `WAQI_TOKEN` to `.env`
  - open the UI with `?source=waqi` or set `DATA_SOURCE=waqi`

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
- Monitoring dashboard data feed with selectable source:
  - `synthetic` (local deterministic demo dataset)
  - `waqi` (real-time WAQI snapshots, token-based)
  - `auto` (attempt real data, fallback to synthetic)
- QA/QC pipeline per station:
  - range checks
  - missing/non-numeric checks
  - spike suspicion checks
  - output split into `measurements_raw` and cleaned `measurements`
- Operational governance controls:
  - append-only audit events (`/api/audit-events`)
  - data quality SLA summary (`/api/data-quality`)
  - simple runtime metrics (`/api/metrics`)
  - Prometheus scrape endpoint (`/metrics`)
  - historical measurement query (`/api/history/station`)
  - operational alerts (`/api/alerts`)
  - automatic retention execution (`/api/history/retention/run`)
  - history backup/restore endpoints (`/api/history/backup`, `/api/history/restore`)
  - configurable rate limiting
  - optional JWT auth + RBAC (`admin` / `viewer`)
- OpenAir-style analytics:
  - Wind rose
  - Polar plot
  - Pollutant time series
- AERMOD-style and CALPUFF-style visualization simulators for plume behavior insights.

## Architecture
- Backend: FastAPI, NumPy/SciPy, SQLAlchemy/PostGIS-ready models.
- Frontend: HTML/CSS/JavaScript with map + chart modules.
- Infra: Docker Compose with PostGIS, Redis, optional Celery worker.

## Architecture Diagram
```mermaid
flowchart LR
    U["User (Browser)"] --> FE["Frontend UI (Leaflet + Chart.js)\nfrontend/index.html + app.js"]

    FE -->|GET /api/health| API["FastAPI Backend\nbackend/main.py"]
    FE -->|GET /api/dashboard-data?source=synthetic| API
    FE -->|GET /api/openair/*| API
    FE -->|GET /api/aermod/dispersion| API
    FE -->|GET /api/calpuff/plume| API
    FE -->|GET /api/emission-sources| API

    API --> DF["Data Fetcher\nbackend/data_fetcher.py\nsources: synthetic | waqi | auto"]
    DF --> WAQI["WAQI API (optional, token-based)"]
    DF --> SYN["Synthetic NTB Generator"]

    API --> QA["QA/QC Engine\nbackend/qa_qc.py\nmissing, range, spike checks"]
    API --> ISPU["ISPU Calculator\nbackend/ispu_calculator.py"]
    API --> CMP["Compliance Checker\nbackend/compliance.py\nPP 22/2021 + WHO 2021"]
    API --> OA["OpenAir-style Analytics\nbackend/met_data.py"]
    API --> AER["AERMOD-style Simulator\nbackend/aermod_simulator.py"]
    API --> CAL["CALPUFF-style Simulator\nbackend/calpuff_simulator.py"]
    API --> SRC["Emission Source Registry\nbackend/emission_sources.py"]

    API --> RESP["JSON Response\n(raw + cleaned + qa_qc + ispu + compliance)"]
    RESP --> FE

    subgraph Deploy["Vercel Deployment"]
      FE
      API
      VCFG["vercel.json\nroutes static + /api/*"]
    end
```

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
   - For the easiest portfolio demo, set `DATA_SOURCE=synthetic`
   - The sample env defaults to SQLite for local-first setup
   - Replace placeholder secrets before enabling auth or public deployment
2. Install backend dependencies:
   ```powershell
   cd backend
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```
3. Run the app:
   ```powershell
   cd ..
   run_dashboard.bat
   ```
   Or start manually:
   ```powershell
   cd backend
   .\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
   ```
4. Open dashboard:
   - [http://127.0.0.1:8000/app/](http://127.0.0.1:8000/app/)
5. Validate key endpoints:
   - [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)
   - [http://127.0.0.1:8000/metrics](http://127.0.0.1:8000/metrics)

## Docker
```bash
docker compose --env-file .env up --build
```

Monitoring stack included in Docker:
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000` using `GRAFANA_ADMIN_USER` and `GRAFANA_ADMIN_PASSWORD` from `.env`
- Alertmanager: `http://localhost:9093`
- Grafana auto-loads `monitoring/grafana/dashboards/airq-overview.json`

## Deploy to Vercel (Quick Test)
1. Push repository to GitHub.
2. Import project in Vercel from that GitHub repo.
3. Set environment variables in Vercel Project Settings:
   - `DATA_SOURCE=synthetic` (recommended for first test)
   - `APP_NAME`
   - `APP_VERSION`
4. Deploy.

Notes:
- `vercel.json` serves `frontend/` as static site and routes `/api/*` to FastAPI serverless entrypoint `api/index.py`.
- Frontend API calls use same-origin paths, so no API URL rewrite is required.

## Testing
```bash
cd backend
pytest -q
```

## CI/CD and Security Automation
- GitHub Actions `CI` workflow:
  - `ruff` lint check
  - `pytest` with coverage gate (>=70%)
  - backup/restore verification drill
  - `pip-audit` vulnerability check
- GitHub Actions `Secret Scan` workflow:
  - `gitleaks` on push/pull request

These pipelines enforce baseline code quality and security checks on every change.

Operational policy docs:
- `docs/AUTH_AND_SECRET_ROTATION_POLICY.md`
- `docs/BACKUP_AND_RETENTION_RUNBOOK.md`

## API Health Check
- `GET /api/health`
- `GET /api/data-quality`
- `GET /api/metrics`
- `GET /metrics` (Prometheus format)
- `GET /api/audit-events` (optionally protected via `x-api-key` when `ADMIN_API_KEY` is set)
- `GET /api/alerts`
- `GET /api/auth/posture`
- `GET /api/history/station?station_id=<id>&pollutant=pm25`
- `POST /api/auth/token` (when `AUTH_ENABLED=true`)
- `POST /api/alerts/dispatch`
- `POST /api/history/retention/run?keep_days=30`
- `POST /api/history/backup`
- `POST /api/history/restore?backup_file=<path>`

## Portfolio Notes for Recruiters
- Prioritizes practical environmental analytics with clear system boundaries.
- Demonstrates ability to connect scientific logic, data services, and geospatial visualization.
- Includes baseline secure configuration practices expected in real deployments.
- Includes an optional SQLAlchemy/PostGIS schema scaffold in `backend/models.py` for future persistence expansion.
