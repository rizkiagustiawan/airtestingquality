from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
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


def is_valid_user(username: str, password: str) -> bool:
    if username == settings.ADMIN_USERNAME and password == settings.ADMIN_PASSWORD:
        return True
    if username == settings.VIEWER_USERNAME and password == settings.VIEWER_PASSWORD:
        return True
    return False


def user_role(username: str) -> str:
    if username == settings.ADMIN_USERNAME:
        return "admin"
    return "viewer"


def create_access_token(username: str, role: str) -> tuple[str, int]:
    expires_in = settings.JWT_EXPIRE_MINUTES * 60
    exp = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    payload = {"sub": username, "role": role, "exp": exp}
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token, expires_in


def get_auth_context(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> AuthContext:
    if not settings.AUTH_ENABLED:
        return AuthContext(username="local-dev", role="admin")

    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc

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
