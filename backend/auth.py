import ipaddress
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import uuid4

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from settings import settings


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    role: str


class AuthContext(BaseModel):
    username: str
    role: str


bearer_scheme = HTTPBearer(auto_error=False)


def is_trusted_request_host(host: str | None) -> bool:
    if not host:
        return False
    normalized = host.strip().lower()
    if normalized in {"127.0.0.1", "::1", "localhost", "testclient"}:
        return True
    try:
        ip = ipaddress.ip_address(normalized)
    except ValueError:
        return False
    return ip.is_loopback or ip.is_private


def is_valid_user(username: str, password: str) -> bool:
    if username == settings.ADMIN_USERNAME and password == settings.ADMIN_PASSWORD:
        return True
    if username == settings.VIEWER_USERNAME and password == settings.VIEWER_PASSWORD:
        return True
    return False


def auth_posture_issues() -> list[dict]:
    issues = []
    if settings.AUTH_ENABLED:
        if settings.ADMIN_PASSWORD == "admin-change-me":
            issues.append(
                {
                    "severity": "critical",
                    "code": "DEFAULT_ADMIN_PASSWORD",
                    "message": "Admin password is still set to the default placeholder.",
                }
            )
        if settings.VIEWER_PASSWORD == "viewer-change-me":
            issues.append(
                {
                    "severity": "warning",
                    "code": "DEFAULT_VIEWER_PASSWORD",
                    "message": "Viewer password is still set to the default placeholder.",
                }
            )
        if len(settings.JWT_SECRETS) < 2:
            issues.append(
                {
                    "severity": "warning",
                    "code": "NO_SECRET_ROTATION_RING",
                    "message": "JWT secret rotation ring has fewer than two active secrets.",
                }
            )
        if settings.JWT_SECRET == "change-me-in-production" and not settings.JWT_SECRETS:
            issues.append(
                {
                    "severity": "critical",
                    "code": "DEFAULT_JWT_SECRET",
                    "message": "JWT secret is still using the insecure default value.",
                }
            )
    return issues


def user_role(username: str) -> str:
    if username == settings.ADMIN_USERNAME:
        return "admin"
    return "viewer"


def create_access_token(username: str, role: str) -> tuple[str, int]:
    expires_in = settings.JWT_EXPIRE_MINUTES * 60
    now = datetime.now(timezone.utc)
    exp = now + timedelta(seconds=expires_in)
    active_kid = settings.JWT_ACTIVE_KID
    secret = settings.JWT_SECRETS.get(active_kid, settings.JWT_SECRET)
    payload = {
        "sub": username,
        "role": role,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "iat": now,
        "nbf": now,
        "exp": exp,
        "jti": str(uuid4()),
    }
    token = jwt.encode(
        payload,
        secret,
        algorithm=settings.JWT_ALGORITHM,
        headers={"kid": active_kid},
    )
    return token, expires_in


def get_auth_context(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    request: Request,
) -> AuthContext:
    if not settings.AUTH_ENABLED:
        request_host = request.client.host if request.client else None
        if is_trusted_request_host(request_host):
            return AuthContext(username="local-dev", role="admin")
        return AuthContext(username="anonymous", role="anonymous")

    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = credentials.credentials
    header = jwt.get_unverified_header(token)
    candidate_secrets: list[str] = []
    header_kid = str(header.get("kid", "")).strip()
    if header_kid and header_kid in settings.JWT_SECRETS:
        candidate_secrets.append(settings.JWT_SECRETS[header_kid])
    for kid, secret in settings.JWT_SECRETS.items():
        if kid != header_kid:
            candidate_secrets.append(secret)

    payload = None
    last_exc: Exception | None = None
    for secret in candidate_secrets:
        try:
            payload = jwt.decode(
                token,
                secret,
                algorithms=[settings.JWT_ALGORITHM],
                audience=settings.JWT_AUDIENCE,
                issuer=settings.JWT_ISSUER,
            )
            break
        except Exception as exc:
            last_exc = exc
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from last_exc

    username = str(payload.get("sub", ""))
    role = str(payload.get("role", "viewer"))
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    return AuthContext(username=username, role=role)


def require_roles(*roles: str):
    def _inner(context: Annotated[AuthContext, Depends(get_auth_context)]) -> AuthContext:
        if roles and context.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return context

    return _inner
