"""Integration tests verifying strict user authorization and IDOR prevention."""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.models.user import User
from app.models.document import Document, DocumentStatus
from app.core.security import create_access_token


def test_user_cannot_access_other_users_document(client: TestClient, db_session):
    """User A cannot access User B's document (returns 404 to prevent IDOR)."""
    # Create User A and User B
    user_a = User(google_id="gid-a", email="user_a@test.com", name="User A")
    user_b = User(google_id="gid-b", email="user_b@test.com", name="User B")
    db_session.add_all([user_a, user_b])
    db_session.commit()
    db_session.refresh(user_a)
    db_session.refresh(user_b)

    # User B owns a document with a valid UUID
    doc_b_id = "550e8400-e29b-41d4-a716-446655440000"
    doc_b = Document(
        id=doc_b_id,
        user_id=user_b.id,
        filename="confidential_b.csv",
        file_type="csv",
        file_path="/tmp/confidential_b.csv",
        status=DocumentStatus.UPLOADED.value
    )
    db_session.add(doc_b)
    db_session.commit()

    token_a = create_access_token(user_a.id, user_a.email)
    token_b = create_access_token(user_b.id, user_b.email)

    # 1. User B can access their own document
    res_b = client.get(
        f"/api/v1/documents/{doc_b.id}",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert res_b.status_code == 200
    assert res_b.json()["document_id"] == doc_b.id

    # 2. User A cannot access User B's document (must return 404, not 403)
    res_a = client.get(
        f"/api/v1/documents/{doc_b.id}",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert res_a.status_code == 404

    # 3. User A cannot access User B's dashboard
    res_dash = client.get(
        f"/api/v1/documents/{doc_b.id}/dashboard",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert res_dash.status_code == 404

    # 4. User A cannot trigger validation on User B's document
    res_val = client.post(
        f"/api/v1/validation/{doc_b.id}/math",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert res_val.status_code == 404


def test_user_document_listing_isolation(client: TestClient, db_session):
    """User listing returns ONLY documents belonging to that user (or legacy unassigned docs)."""
    user_x = User(google_id="gid-x", email="x@test.com", name="User X")
    user_y = User(google_id="gid-y", email="y@test.com", name="User Y")
    db_session.add_all([user_x, user_y])
    db_session.commit()
    db_session.refresh(user_x)
    db_session.refresh(user_y)

    doc_x = Document(
        id="doc-x-1",
        user_id=user_x.id,
        filename="statement_x.csv",
        file_type="csv",
        file_path="/tmp/statement_x.csv",
        status=DocumentStatus.UPLOADED.value
    )
    doc_y = Document(
        id="doc-y-1",
        user_id=user_y.id,
        filename="statement_y.csv",
        file_type="csv",
        file_path="/tmp/statement_y.csv",
        status=DocumentStatus.UPLOADED.value
    )
    db_session.add_all([doc_x, doc_y])
    db_session.commit()

    token_x = create_access_token(user_x.id, user_x.email)
    res_list_x = client.get(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {token_x}"}
    )
    assert res_list_x.status_code == 200
    doc_ids_x = [d["document_id"] for d in res_list_x.json()["documents"]]
    assert doc_x.id in doc_ids_x
    assert doc_y.id not in doc_ids_x
