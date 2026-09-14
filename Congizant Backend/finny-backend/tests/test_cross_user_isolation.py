"""Full end-to-end integration test with multiple authenticated users and complete pipeline."""

import pytest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.models.user import User
from app.models.document import Document, DocumentStatus
from app.core.security import create_access_token


def test_cross_user_complete_pipeline_isolation(client: TestClient, sample_csv: Path, db_session):
    """
    Mandatory full E2E test with two users:
    1. User A logs in via Google flow
    2. User A uploads and processes financial document
    3. User A runs full math, YoY, ratio, ML analysis
    4. User B logs in
    5. Verify User B CANNOT access User A's document, dashboard, analysis, reports, or chat
    """
    # 1. Create User A and User B
    user_a = User(google_id="gid-alpha", email="alice@firm.com", name="Alice CFO")
    user_b = User(google_id="gid-beta", email="bob@competitor.com", name="Bob Analyst")
    db_session.add_all([user_a, user_b])
    db_session.commit()
    db_session.refresh(user_a)
    db_session.refresh(user_b)

    token_a = create_access_token(user_a.id, user_a.email)
    token_b = create_access_token(user_b.id, user_b.email)

    # 2. User A uploads statement
    with open(sample_csv, "rb") as f:
        upload_res = client.post(
            "/api/v1/documents/upload",
            files={"file": ("alice_financials.csv", f, "text/csv")},
            headers={"Authorization": f"Bearer {token_a}"}
        )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["document_id"]

    # 3. User A processes statement (extraction + normalization)
    proc_res = client.post(
        f"/api/v1/documents/{doc_id}/process",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert proc_res.status_code == 200

    # 4. User A runs Math Validation
    math_res = client.post(
        f"/api/v1/validation/{doc_id}/math",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert math_res.status_code == 200

    # 5. User A runs YoY Analysis
    yoy_res = client.post(
        f"/api/v1/analysis/{doc_id}/yoy",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert yoy_res.status_code == 200

    # 6. User A runs Ratios
    ratio_res = client.post(
        f"/api/v1/analysis/{doc_id}/ratios",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert ratio_res.status_code == 200

    # 7. User A accesses dashboard summary
    dash_res = client.get(
        f"/api/v1/documents/{doc_id}/dashboard",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert dash_res.status_code == 200

    # 8. User A checks reports listing
    rep_res = client.get(
        "/api/v1/reports",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert rep_res.status_code == 200
    user_a_doc_ids = [d["document_id"] for d in rep_res.json()["documents"]]
    assert doc_id in user_a_doc_ids

    # =========================================================================
    # USER B ISOLATION VERIFICATION — ALL CROSS-USER ATTEMPTS MUST RETURN 404
    # =========================================================================

    # Attempt 1: User B tries to view Alice's document status
    res_b_doc = client.get(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert res_b_doc.status_code == 404

    # Attempt 2: User B tries to fetch Alice's normalized data
    res_b_norm = client.get(
        f"/api/v1/documents/{doc_id}/normalized",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert res_b_norm.status_code == 404

    # Attempt 3: User B tries to view Alice's dashboard
    res_b_dash = client.get(
        f"/api/v1/documents/{doc_id}/dashboard",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert res_b_dash.status_code == 404

    # Attempt 4: User B tries to view Alice's report details
    res_b_rep = client.get(
        f"/api/v1/reports/{doc_id}",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert res_b_rep.status_code == 404

    # Attempt 5: User B lists reports -> must NOT see Alice's document
    res_b_rep_list = client.get(
        "/api/v1/reports",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert res_b_rep_list.status_code == 200
    user_b_doc_ids = [d["document_id"] for d in res_b_rep_list.json()["documents"]]
    assert doc_id not in user_b_doc_ids

    # Attempt 6: User B attempts to chat about Alice's document
    res_b_chat = client.post(
        f"/api/v1/chat/{doc_id}",
        json={"message": "Give me the net income"},
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert res_b_chat.status_code == 404
