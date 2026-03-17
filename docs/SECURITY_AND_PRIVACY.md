# Security and Privacy Baseline

## Implemented in This Repo
- Secrets moved to environment variables (`.env` pattern).
- Default local database fallback avoids committing live credentials.
- CORS policy is configurable and no longer hardcoded to wildcard by default.
- Basic API health endpoint for operational monitoring.

## Required Before Production
- Rotate `SECRET_KEY` and database credentials.
- Enforce HTTPS and secure reverse proxy.
- Add authentication/authorization policy for protected endpoints.
- Add privacy notice and lawful basis mapping if personal data is processed.
- Add DSAR handling flow if serving jurisdictions with data subject rights.

## Operational Best Practices
- Keep `.env` out of version control.
- Use separate credentials per environment (dev/staging/prod).
- Add CI checks for secret scanning and dependency vulnerabilities.
