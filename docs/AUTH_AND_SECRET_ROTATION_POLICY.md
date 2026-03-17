# Auth And Secret Rotation Policy

## Scope
This document defines the minimum operational policy for JWT authentication and role-based access control in this repository.

## Roles
- `admin`: full access to operational and governance endpoints.
- `viewer`: read access to approved monitoring/history endpoints.

## JWT Requirements
- Enable auth in non-local environments with `AUTH_ENABLED=true`.
- Configure `JWT_ACTIVE_KID` and `JWT_SECRETS` so at least two secrets are available during rotation.
- Each JWT must include:
  - `kid`
  - `iss`
  - `aud`
  - `iat`
  - `nbf`
  - `exp`
  - `jti`

## Rotation Procedure
1. Add a new secret to `JWT_SECRETS` with a new key id, for example `v3:new-secret`.
2. Set `JWT_ACTIVE_KID=v3`.
3. Redeploy services.
4. Allow old tokens signed by previous `kid` to expire naturally.
5. Remove old secret from `JWT_SECRETS` after expiry window has passed.

## Credential Policy
- Default placeholder passwords must never be used outside local development.
- Admin credentials must be rotated on environment bootstrap and after any suspected exposure.
- Secrets must be stored in a secret manager or encrypted deployment variable store.

## Audit Expectations
- Review `/api/auth/posture` after every rotation.
- Record rotation date, actor, environment, and retired key id in change management records.
