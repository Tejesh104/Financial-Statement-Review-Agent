"""Unit and integration tests for Google Sign-In and JWT authentication."""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.models.user import User
from app.core.security import create_access_token, decode_access_token


def test_jwt_create_and_decode():
    """Verify JWT token encoding, decoding, and payload contents."""
    token = create_access_token(user_id="user-123", email="test@example.com")
    assert isinstance(token, str)
    assert len(token) > 20

    payload = decode_access_token(token)
    assert payload["sub"] == "user-123"
    assert payload["email"] == "test@example.com"
    assert payload["type"] == "access"
    assert "exp" in payload


def test_auth_me_unauthenticated(client: TestClient):
    """Accessing /auth/me without token returns 401 Unauthorized."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert "Authentication required" in response.json()["detail"]


def test_auth_me_invalid_token(client: TestClient):
    """Accessing /auth/me with an invalid token returns 401 Unauthorized."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.value"}
    )
    assert response.status_code == 401


def test_auth_me_authenticated(client: TestClient, db_session):
    """Accessing /auth/me with valid token returns user profile."""
    # Create test user
    user = User(
        google_id="google-sub-123",
        email="analyst@finny.com",
        name="Finny Analyst",
        picture_url="https://example.com/photo.jpg"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = create_access_token(user.id, user.email)
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user.id
    assert data["email"] == "analyst@finny.com"
    assert data["name"] == "Finny Analyst"


@patch("app.api.routes.auth.verify_google_id_token")
def test_google_auth_flow(mock_verify, client: TestClient, db_session):
    """Simulate complete Google Sign-In: new user registration and existing user login."""
    mock_verify.return_value = {
        "sub": "google-oauth-unique-id",
        "email": "cfo@company.com",
        "name": "Chief Financial Officer",
        "picture": "https://company.com/cfo.png",
        "email_verified": True
    }

    # 1. First login -> creates new user
    res1 = client.post(
        "/api/v1/auth/google",
        json={"id_token": "valid-mock-google-token"}
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert "access_token" in data1
    assert data1["user"]["email"] == "cfo@company.com"
    user_id = data1["user"]["id"]

    # Verify user saved in DB
    user_in_db = db_session.query(User).filter(User.id == user_id).first()
    assert user_in_db is not None
    assert user_in_db.google_id == "google-oauth-unique-id"

    # 2. Second login -> recognizes existing user
    res2 = client.post(
        "/api/v1/auth/google",
        json={"id_token": "valid-mock-google-token"}
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["user"]["id"] == user_id  # Same user ID


def test_logout(client: TestClient, db_session):
    """Test advisory logout endpoint."""
    user = User(google_id="gid-logout", email="logout@example.com", name="Logout User")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = create_access_token(user.id, user.email)
    res = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    assert "Logged out successfully" in res.json()["message"]
