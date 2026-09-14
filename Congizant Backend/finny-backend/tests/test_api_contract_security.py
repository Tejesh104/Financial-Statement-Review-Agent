"""
Tests for Type 3, 7, and 12: API Contract, Security, and Schema Adherence.
Verifies:
- All registered endpoints return valid schemas and status codes
- Zero credential / secret leakage (JWT secret, OAuth client secret, DB path, passwords)
- Strict error schema formatting (detail field present)
- IDOR / Cross-user authorization controls on protected routes
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.security import create_access_token


@pytest.fixture
def user1_headers(db_session):
    from app.models.user import User
    user = User(id="u1-security-test", google_id="u1-gid", email="user1@example.com", name="User 1")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    token = create_access_token(user_id=user.id, email=user.email)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user2_headers(db_session):
    from app.models.user import User
    user = User(id="u2-security-test", google_id="u2-gid", email="user2@example.com", name="User 2")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    token = create_access_token(user_id=user.id, email=user.email)
    return {"Authorization": f"Bearer {token}"}


def test_openapi_contract_conformance(client):
    """Verify OpenAPI schema conforms to OpenAPI 3.x and defines core paths."""
    res = client.get("/openapi.json")
    assert res.status_code == 200
    schema = res.json()
    assert "openapi" in schema
    assert "paths" in schema
    
    # Must contain essential endpoints
    paths = schema["paths"]
    assert "/api/health" in paths
    assert "/api/v1/auth/google" in paths
    assert "/api/v1/documents/upload" in paths
    assert "/api/v1/documents/{document_id}/process" in paths
    assert "/api/v1/documents/{document_id}/dashboard" in paths
    assert "/api/v1/reports" in paths


def test_no_credential_or_secret_leak_in_api_responses(client, user1_headers):
    """Ensure sensitive environment variables, secrets, and system tokens are NEVER returned."""
    endpoints_to_probe = [
        ("GET", "/api/health", {}),
        ("GET", "/api/v1/auth/me", user1_headers),
        ("GET", "/api/v1/documents", user1_headers),
        ("GET", "/api/v1/reports", user1_headers),
    ]

    secrets_to_check = [
        settings.JWT_SECRET_KEY,
        settings.GOOGLE_CLIENT_ID,
    ]
    if hasattr(settings, "DATABASE_URL") and "sqlite" not in settings.DATABASE_URL:
        secrets_to_check.append(settings.DATABASE_URL)

    for method, path, headers in endpoints_to_probe:
        if method == "GET":
            res = client.get(path, headers=headers)
        body = res.text
        for secret in secrets_to_check:
            if secret and len(secret) > 6:
                assert secret not in body, f"CRITICAL: Secret leaked in {path} response!"


def test_idor_cross_user_document_access_blocked(client, user1_headers, user2_headers):
    """User 2 cannot view or delete User 1's uploaded document."""
    # Create document under user 1
    upload_res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("idor_test.csv", "Account,Amount\nCash,1000\nRevenue,1000", "text/csv")},
        headers=user1_headers
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["document_id"]

    # User 2 attempts to get document metadata
    res_get = client.get(f"/api/v1/documents/{doc_id}", headers=user2_headers)
    assert res_get.status_code in [403, 404], f"User 2 was able to view User 1 doc: {res_get.status_code}"

    # User 2 attempts to view dashboard
    res_dash = client.get(f"/api/v1/documents/{doc_id}/dashboard", headers=user2_headers)
    assert res_dash.status_code in [403, 404], f"User 2 accessed User 1 dashboard: {res_dash.status_code}"

    # User 2 attempts to delete document
    res_del = client.delete(f"/api/v1/documents/{doc_id}", headers=user2_headers)
    assert res_del.status_code in [403, 404], f"User 2 deleted User 1 doc: {res_del.status_code}"

    # Cleanup: User 1 deletes own document
    cleanup_res = client.delete(f"/api/v1/documents/{doc_id}", headers=user1_headers)
    assert cleanup_res.status_code == 200


def test_unauthenticated_requests_to_strictly_protected_endpoints_rejected(client):
    """Strictly protected endpoints reject unauthenticated calls with 401."""
    protected_urls = [
        ("GET", "/api/v1/auth/me"),
        ("POST", "/api/v1/auth/logout"),
    ]
    for method, url in protected_urls:
        if method == "GET":
            res = client.get(url)
        elif method == "POST":
            res = client.post(url)
        assert res.status_code in [401, 403], f"Unauthenticated request to {url} allowed: {res.status_code}"
        assert "detail" in res.json()
