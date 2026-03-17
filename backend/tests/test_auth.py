import auth


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
    context = auth.get_auth_context(creds)
    assert context.username == "viewer"
    assert context.role == "viewer"
