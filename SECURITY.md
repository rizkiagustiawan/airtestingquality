# Security Policy

## Supported Use

This repository is maintained as a public portfolio project with production-minded practices, but it is not represented as a certified regulatory platform.

## Reporting a Vulnerability

Please do not open a public issue for sensitive vulnerabilities.

Instead, report security concerns privately to the repository owner with:
- a short description of the issue
- reproduction steps
- impact assessment
- suggested remediation if available

## Expected Security Practices

- Secrets belong in `.env`, platform secret stores, or CI/CD secret managers.
- Placeholder credentials in `.env.example` must be replaced before non-local deployment.
- Public deployments should enable strong secrets, restrictive CORS, and non-default auth credentials.

## Current Controls in This Repo

- GitHub Actions CI
- secret scanning with `gitleaks`
- dependency audit with `pip-audit`
- configurable JWT auth and secret rotation ring
- audit trail, backup, retention, and metrics endpoints

## Scope Notes

- Synthetic demo mode is the safest default for public review.
- Real-data mode requires external credentials and should be validated per deployment context.
