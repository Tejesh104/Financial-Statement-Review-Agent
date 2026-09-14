"""End-to-end integration and API tests for Agent 2 Review."""

import json
import uuid
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.database import SessionLocal
from app.models.document import Document, DocumentStatus
from app.models.financial_data import FinancialData
from app.schemas.agent2 import OllamaReviewContent, ObservationFinding


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def mock_ollama():
    with patch("app.services.agent2.ollama_client.OllamaClient.generate_review") as mock_gen:
        mock_gen.return_value = OllamaReviewContent(
            observations=[
                ObservationFinding(
                    finding_type="VALIDATION",
                    title="Balance Sheet Equality",
                    finding="Assets match liabilities plus equity.",
                    explanation="Mathematical balance holds within tolerance.",
                    severity="LOW",
                    evidence=["findings.validations.balance_sheet_check"]
                ),
                ObservationFinding(
                    finding_type="YOY",
                    title="Revenue Growth",
                    finding="Revenue increased by 20.00%.",
                    explanation="Revenue grew from 1,000,000 to 1,200,000.",
                    severity="LOW",
                    evidence=["findings.variances.revenue"]
                )
            ],
            summary="Financial statements show consistent balance and top-line growth.",
            limitations=[]
        )
        yield mock_gen


def test_api_review_invalid_uuid(client):
    res = client.post("/api/v1/agent2/invalid-uuid/review")
    assert res.status_code == 400
    assert "Expected a valid UUID" in res.json()["detail"]


def test_api_review_nonexistent_doc(client):
    random_id = str(uuid.uuid4())
    res = client.post(f"/api/v1/agent2/{random_id}/review")
    assert res.status_code == 404
    assert f"Document with ID '{random_id}' not found" in res.json()["detail"]


def test_api_review_unnormalized_doc(client, db_session):
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="unnorm.pdf",
        file_type="pdf",
        file_path="uploads/unnorm.pdf",
        status=DocumentStatus.UPLOADED.value,
    )
    db_session.add(doc)
    db_session.commit()

    res = client.post(f"/api/v1/agent2/{doc_id}/review")
    assert res.status_code == 400
    assert "has not been normalized yet" in res.json()["detail"]


def test_api_review_success_with_persistence(client, db_session, mock_ollama):
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="success.pdf",
        file_type="pdf",
        file_path="uploads/success.pdf",
        status=DocumentStatus.NORMALIZED.value,
    )
    db_session.add(doc)

    fin_data = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        company_name="Review Corp",
        fiscal_year="2024",
        revenue=1200000.0,
        assets=2400000.0,
        liabilities=1000000.0,
        equity=1400000.0,
        normalized_data={
            "financial_data": {
                "revenue": 1200000.0,
                "gross_profit": 500000.0,
                "net_profit": 200000.0,
                "assets": 2400000.0,
                "liabilities": 1000000.0,
                "equity": 1400000.0,
                "current_assets": 800000.0,
                "current_liabilities": 400000.0,
                "inventory": 100000.0,
            },
            "previous_period_data": {
                "period": "2023",
                "financial_data": {
                    "revenue": 1000000.0,
                    "gross_profit": 400000.0,
                    "net_profit": 150000.0,
                    "assets": 2000000.0,
                    "liabilities": 800000.0,
                    "equity": 1200000.0,
                    "current_assets": 700000.0,
                    "current_liabilities": 350000.0,
                    "inventory": 90000.0,
                }
            }
        }
    )
    db_session.add(fin_data)
    db_session.commit()

    res = client.post(f"/api/v1/agent2/{doc_id}/review")
    assert res.status_code == 200
    data = res.json()
    assert data["document_id"] == doc_id
    assert data["status"] in ("COMPLETED", "PARTIAL")
    assert len(data["investigations"]) > 0
    assert len(data["metric_comparisons"]) > 0
    assert len(data["observations"]) == 2
    assert "consistent balance" in data["summary"]

    # Verify atomic DB persistence under normalized_data['analysis']['agent2']
    db_session.expire_all()
    rec = db_session.query(FinancialData).filter(FinancialData.document_id == doc_id).first()
    norm = rec.normalized_data
    assert "analysis" in norm
    assert "agent2" in norm["analysis"]
    assert "agent1_findings" in norm["analysis"]
    assert norm["analysis"]["agent2"]["status"] in ("COMPLETED", "PARTIAL")


def test_api_review_ollama_unavailable_503(client, db_session):
    from app.services.agent2.ollama_client import OllamaUnavailableException
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="unav.pdf",
        file_type="pdf",
        file_path="uploads/unav.pdf",
        status=DocumentStatus.NORMALIZED.value,
    )
    db_session.add(doc)
    fin_data = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        normalized_data={"financial_data": {"revenue": 1000.0}}
    )
    db_session.add(fin_data)
    db_session.commit()

    with patch("app.services.agent2.ollama_client.OllamaClient.generate_review", side_effect=OllamaUnavailableException("Connection refused")):
        res = client.post(f"/api/v1/agent2/{doc_id}/review")
        assert res.status_code == 503
        assert "unavailable" in res.json()["detail"].lower()


def test_api_review_ollama_timeout_504(client, db_session):
    from app.services.agent2.ollama_client import OllamaTimeoutException
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="timeout.pdf",
        file_type="pdf",
        file_path="uploads/timeout.pdf",
        status=DocumentStatus.NORMALIZED.value,
    )
    db_session.add(doc)
    fin_data = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        normalized_data={"financial_data": {"revenue": 1000.0}}
    )
    db_session.add(fin_data)
    db_session.commit()

    with patch("app.services.agent2.ollama_client.OllamaClient.generate_review", side_effect=OllamaTimeoutException("Timed out")):
        res = client.post(f"/api/v1/agent2/{doc_id}/review")
        assert res.status_code == 504
        assert "timed out" in res.json()["detail"].lower()


def test_api_review_idempotency_and_sibling_preservation(client, db_session, mock_ollama):
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="idem.pdf",
        file_type="pdf",
        file_path="uploads/idem.pdf",
        status=DocumentStatus.NORMALIZED.value,
    )
    db_session.add(doc)
    fin_data = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        revenue=500000.0,
        assets=1000000.0,
        liabilities=400000.0,
        equity=600000.0,
        normalized_data={
            "financial_data": {"revenue": 500000.0, "assets": 1000000.0, "liabilities": 400000.0, "equity": 600000.0},
            "custom_metadata": "keep_me"
        }
    )
    db_session.add(fin_data)
    db_session.commit()

    # Call twice
    res1 = client.post(f"/api/v1/agent2/{doc_id}/review")
    assert res1.status_code == 200
    res2 = client.post(f"/api/v1/agent2/{doc_id}/review")
    assert res2.status_code == 200

    db_session.expire_all()
    rec = db_session.query(FinancialData).filter(FinancialData.document_id == doc_id).first()
    assert rec.normalized_data["custom_metadata"] == "keep_me"
    assert "agent2" in rec.normalized_data["analysis"]


def test_api_review_malformed_ollama_502(client, db_session):
    from app.services.agent2.ollama_client import OllamaMalformedResponseException
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="malformed.pdf",
        file_type="pdf",
        file_path="uploads/malformed.pdf",
        status=DocumentStatus.NORMALIZED.value,
    )
    db_session.add(doc)
    fin_data = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        normalized_data={"financial_data": {"revenue": 1000.0}}
    )
    db_session.add(fin_data)
    db_session.commit()

    with patch("app.services.agent2.ollama_client.OllamaClient.generate_review", side_effect=OllamaMalformedResponseException("Invalid JSON")):
        res = client.post(f"/api/v1/agent2/{doc_id}/review")
        assert res.status_code == 502
        assert "malformed" in res.json()["detail"].lower()


def test_api_review_rollback_on_db_error(client, db_session, mock_ollama, monkeypatch):
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="rollback.pdf",
        file_type="pdf",
        file_path="uploads/rollback.pdf",
        status=DocumentStatus.NORMALIZED.value,
    )
    db_session.add(doc)
    fin_data = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        normalized_data={"financial_data": {"revenue": 1000.0}}
    )
    db_session.add(fin_data)
    db_session.commit()

    from sqlalchemy.orm import Session
    def mock_commit(self):
        raise RuntimeError("Simulated DB failure")

    monkeypatch.setattr(Session, "commit", mock_commit)

    res = client.post(f"/api/v1/agent2/{doc_id}/review")
    assert res.status_code == 500
    assert "Failed to persist" in res.json()["detail"] or "error" in res.json()["detail"].lower()


def test_live_ollama_execution(client, db_session):
    """Optional live Ollama test: runs against real local Ollama server if running."""
    import urllib.request
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2) as resp:
            if resp.status != 200:
                pytest.skip("Local Ollama not available")
    except Exception:
        pytest.skip("Local Ollama not reachable")

    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="live_test.pdf",
        file_type="pdf",
        file_path="uploads/live_test.pdf",
        status=DocumentStatus.NORMALIZED.value,
    )
    db_session.add(doc)
    fin_data = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        company_name="Live Ollama Co",
        fiscal_year="2024",
        revenue=2500000.0,
        assets=5000000.0,
        liabilities=2000000.0,
        equity=3000000.0,
        normalized_data={
            "financial_data": {
                "revenue": 2500000.0,
                "gross_profit": 1000000.0,
                "net_profit": 400000.0,
                "assets": 5000000.0,
                "liabilities": 2000000.0,
                "equity": 3000000.0,
                "current_assets": 1500000.0,
                "current_liabilities": 800000.0,
                "inventory": 200000.0,
            }
        }
    )
    db_session.add(fin_data)
    db_session.commit()

    # Call Agent 2 review endpoint (runs live against Ollama)
    res = client.post(f"/api/v1/agent2/{doc_id}/review")
    if res.status_code == 504:
        pytest.skip("Local Ollama timed out due to CPU load during test run")
    assert res.status_code == 200
    payload = res.json()
    assert payload["status"] in ("COMPLETED", "PARTIAL")
    assert len(payload["investigations"]) > 0
    assert len(payload["metric_comparisons"]) > 0
    assert payload["model"] == "qwen2.5:7b"
