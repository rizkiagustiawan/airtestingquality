# Backup And Retention Runbook

## Purpose
This runbook defines how to operate retention, backup, and restore controls for the historical measurement store.

## Retention
- Default retention window is controlled by `RETENTION_DAYS`.
- Manual execution endpoint:
  - `POST /api/history/retention/run?keep_days=<n>`
- Run retention at least daily in persistent environments.

## Backup
- Manual backup endpoint:
  - `POST /api/history/backup`
- Backup output is stored under the runtime backup directory.
- Keep at least one tested restore point outside the primary runtime directory.

## Restore
- Restore endpoint:
  - `POST /api/history/restore?backup_file=<absolute path>`
- Always restore first in a staging environment when feasible.
- Validate record counts and a sample station history after restore.

## Verification Drill
The CI pipeline includes an automated backup-restore drill using `tests/test_history_store.py`.

## Audit Evidence
- Backup event records are appended to the audit log.
- Restore event records are appended to the audit log.
- Retention executions are appended to the audit log with cutoff and deletion counts.
