import auth


class _DummyClient:
    def __init__(self, host: str):
        self.host = host


class _DummyRequest:
    def __init__(self, host: str):
        self.client = _DummyClient(host)


def test_create_access_token_uses_active_kid(monkeypatch):
    long_old_secret = "old-secret-32-bytes-minimum-value-123"
    long_new_secret = "new-secret-32-bytes-minimum-value-456"
    long_fallback_secret = "fallback-secret-32-bytes-minimum-789"
    monkeypatch.setattr(auth.settings, "JWT_ACTIVE_KID", "v2")
    monkeypatch.setattr(
        auth.settings,
        "JWT_SECRETS",
        {"v1": long_old_secret, "v2": long_new_secret},
    )
    monkeypatch.setattr(auth.settings, "JWT_SECRET", long_fallback_secret)
    monkeypatch.setattr(auth.settings, "JWT_ISSUER", "airq-webgis")
    monkeypatch.setattr(auth.settings, "JWT_AUDIENCE", "airq-api")
    token, _ = auth.create_access_token("admin", "admin")
    header = auth.jwt.get_unverified_header(token)
    assert header["kid"] == "v2"


def test_get_auth_context_accepts_previous_secret(monkeypatch):
    long_old_secret = "old-secret-32-bytes-minimum-value-123"
    long_new_secret = "new-secret-32-bytes-minimum-value-456"
    long_fallback_secret = "fallback-secret-32-bytes-minimum-789"
    monkeypatch.setattr(auth.settings, "AUTH_ENABLED", True)
    monkeypatch.setattr(auth.settings, "JWT_ACTIVE_KID", "v2")
    monkeypatch.setattr(
        auth.settings,
        "JWT_SECRETS",
        {"v1": long_old_secret, "v2": long_new_secret},
    )
    monkeypatch.setattr(auth.settings, "JWT_SECRET", long_fallback_secret)
    monkeypatch.setattr(auth.settings, "JWT_ISSUER", "airq-webgis")
    monkeypatch.setattr(auth.settings, "JWT_AUDIENCE", "airq-api")

    token = auth.jwt.encode(
        {
            "sub": "viewer",
            "role": "viewer",
            "iss": "airq-webgis",
            "aud": "airq-api",
            "iat": 1700000000,
            "nbf": 1700000000,
            "exp": 4102444800,
            "jti": "legacy-token",
        },
        long_old_secret,
        algorithm="HS256",
        headers={"kid": "v1"},
    )

    creds = auth.HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    context = auth.get_auth_context(creds, _DummyRequest("127.0.0.1"))
    assert context.username == "viewer"
    assert context.role == "viewer"


def test_get_auth_context_returns_anonymous_for_remote_when_auth_disabled(monkeypatch):
    monkeypatch.setattr(auth.settings, "AUTH_ENABLED", False)
    context = auth.get_auth_context(None, _DummyRequest("203.0.113.10"))
    assert context.username == "anonymous"
    assert context.role == "anonymous"


def test_is_trusted_request_host_accepts_private_and_loopback_hosts():
    assert auth.is_trusted_request_host("127.0.0.1") is True
    assert auth.is_trusted_request_host("172.20.0.3") is True
    assert auth.is_trusted_request_host("203.0.113.10") is False
