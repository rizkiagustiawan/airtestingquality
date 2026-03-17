# Security and Privacy Baseline

## Implemented in This Repo
- Secrets moved to environment variables (`.env` pattern).
- Default local database fallback avoids committing live credentials.
- CORS policy is configurable and no longer hardcoded to wildcard by default.
- Basic API health endpoint for operational monitoring.
- JWT auth supports multiple secrets for staged key rotation.
- Auth posture can be reviewed via operational API and policy docs.

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
- Follow the rotation procedure in `docs/AUTH_AND_SECRET_ROTATION_POLICY.md`.
- Follow the backup/restore procedure in `docs/BACKUP_AND_RETENTION_RUNBOOK.md`.
