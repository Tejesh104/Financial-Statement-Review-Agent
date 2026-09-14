"""Unit and integration tests for Finny Dashboard API endpoints."""

import io
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.database import SessionLocal
from app.models.document import Document, DocumentStatus
from app.models.financial_data import FinancialData


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


def test_list_documents_endpoint(client, db_session):
    """Verify GET /api/v1/documents returns document list conforming to schema."""
    res = client.get("/api/v1/documents")
    assert res.status_code == 200
    data = res.json()
    assert "total" in data
    assert "documents" in data
    assert isinstance(data["documents"], list)
    assert data["total"] == len(data["documents"])


def test_dashboard_summary_404_for_unknown_document(client):
    """Verify GET /api/v1/documents/{unknown_id}/dashboard returns 404."""
    unknown_id = str(uuid.uuid4())
    res = client.get(f"/api/v1/documents/{unknown_id}/dashboard")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_dashboard_summary_unprocessed_document(client, db_session):
    """Verify dashboard summary handles an uploaded but unprocessed document gracefully."""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="unprocessed_test.csv",
        file_type="csv",
        file_path="uploads/unprocessed_test.csv",
        status=DocumentStatus.UPLOADED.value,
    )
    db_session.add(doc)
    db_session.commit()

    res = client.get(f"/api/v1/documents/{doc_id}/dashboard")
    assert res.status_code == 200
    data = res.json()
    assert data["document_id"] == doc_id
    assert data["status"] == "UPLOADED"
    assert data["pipeline"]["uploaded"] is True
    assert data["pipeline"]["normalized"] is False
    assert data["risk"]["tier"] in ("LOW", "MEDIUM", "HIGH")


def test_dashboard_summary_full_document(client, db_session):
    """Verify consolidated dashboard response with complete analytical layers."""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="full_dashboard_test.csv",
        file_type="csv",
        file_path="uploads/full_dashboard_test.csv",
        status=DocumentStatus.NORMALIZED.value,
    )
    db_session.add(doc)

    fin = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        company_name="Acme Global Inc.",
        currency="USD",
        fiscal_year="2024",
        revenue=1000000.0,
        assets=5000000.0,
        liabilities=2000000.0,
        equity=3000000.0,
        normalized_data={
            "document_id": doc_id,
            "company": {"name": "Acme Global Inc."},
            "currency": "USD",
            "period": {"fiscal_year": "2024"},
            "financial_data": {
                "revenue": 1000000.0,
                "assets": 5000000.0,
                "liabilities": 2000000.0,
                "equity": 3000000.0,
            },
            "validation": {
                "balance_sheet_check": {
                    "status": "VALID",
                    "difference": 0.0,
                    "tolerance": 1.0,
                }
            },
            "analysis": {
                "yoy": {
                    "status": "COMPLETED",
                    "periods": {"previous_period": "2023", "current_period": "2024"},
                    "financial_data": {
                        "revenue": {
                            "current_value": 1000000.0,
                            "previous_value": 800000.0,
                            "percentage_change": 25.0,
                            "direction": "positive",
                            "status": "COMPLETED",
                        }
                    },
                },
                "ratios": {
                    "status": "COMPLETED",
                    "ratios": {
                        "liquidity": {"current_ratio": {"value": 2.5, "status": "COMPLETED"}},
                    },
                },
                "agent1": {"status": "COMPLETED"},
                "agent1_findings": {
                    "document_id": doc_id,
                    "status": "COMPLETED",
                    "findings": {
                        "validations": [],
                        "variances": [],
                        "anomalies": [],
                        "ratios": [],
                        "evidence": [],
                    },
                },
                "agent2": {
                    "document_id": doc_id,
                    "status": "COMPLETED",
                    "summary": "Financial health is stable.",
                    "investigations": [],
                    "metric_comparisons": [],
                    "observations": [],
                    "model": "qwen2.5:7b",
                },
            },
            "ml_anomaly": {
                "document_id": doc_id,
                "status": "COMPLETED",
                "classification": "NORMAL",
                "anomaly_score": 0.125,
                "prediction": 1,
                "is_anomaly": False,
                "model": {
                    "type": "IsolationForest",
                    "version": "1.8.0",
                    "training_dataset": "Financial Statements.csv",
                    "feature_count": 6,
                },
                "features": {"current_ratio": 2.5},
                "anomaly_detection": {"prediction": 1, "score": 0.125, "is_anomaly": False},
            },
            "review_observations": {
                "document_id": doc_id,
                "status": "COMPLETED",
                "observations": [
                    {
                        "finding": "Balance sheet balances.",
                        "explanation": "Assets equal liabilities plus equity.",
                        "severity": "LOW",
                        "evidence": [{"field": "balance_sheet", "source": "validation", "value": 0.0}],
                        "recommendation": "Maintain standard quarterly audit records.",
                    }
                ],
                "summary": "No critical accounting anomalies detected.",
                "model": "qwen2.5:7b",
            },
        },
    )
    db_session.add(fin)
    db_session.commit()

    res = client.get(f"/api/v1/documents/{doc_id}/dashboard")
    assert res.status_code == 200
    data = res.json()
    assert data["company_name"] == "Acme Global Inc."
    assert data["pipeline"]["validated"] is True
    assert data["pipeline"]["observations_ready"] is True
    assert data["risk"]["tier"] == "LOW"
    assert data["risk"]["score"] == 0.125
    assert len(data["review_observations"]["observations"]) == 1


def test_delete_document_endpoint_success(client, db_session, tmp_path):
    """Verify DELETE /api/v1/documents/{id} removes document, cascaded records, and file."""
    # Create temp file
    dummy_file = tmp_path / "delete_me.csv"
    dummy_file.write_text("Revenue,100\n", encoding="utf-8")

    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="delete_me.csv",
        file_type="csv",
        file_path=str(dummy_file),
        status=DocumentStatus.NORMALIZED.value,
    )
    fin = FinancialData(
        document_id=doc_id,
        company_name="Delete Corp",
        currency="USD",
        revenue=100.0,
        assets=200.0,
        liabilities=100.0,
        equity=100.0,
        normalized_data={"financial_data": {"revenue": 100.0}},
    )
    db_session.add(doc)
    db_session.add(fin)
    db_session.commit()

    # Delete via API
    del_res = client.delete(f"/api/v1/documents/{doc_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"
    assert del_res.json()["document_id"] == doc_id

    # Verify document no longer exists in DB
    assert db_session.query(Document).filter(Document.id == doc_id).first() is None
    assert db_session.query(FinancialData).filter(FinancialData.document_id == doc_id).first() is None

    # Verify physical file unlinked
    assert not dummy_file.exists()

    # Subsequent GET should return 404
    get_res = client.get(f"/api/v1/documents/{doc_id}")
    assert get_res.status_code == 404


def test_delete_document_not_found(client):
    """Verify DELETE /api/v1/documents/{id} returns 404 for unknown document."""
    unknown_id = str(uuid.uuid4())
    del_res = client.delete(f"/api/v1/documents/{unknown_id}")
    assert del_res.status_code == 404


