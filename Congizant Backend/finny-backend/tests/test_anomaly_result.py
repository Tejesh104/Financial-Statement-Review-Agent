"""Comprehensive unit and integration tests for Step 3.5 Anomaly Detection Result."""

import uuid
import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database.database import SessionLocal, get_db
from app.models.document import Document, DocumentStatus
from app.models.financial_data import FinancialData
from app.services.ml.anomaly_result_builder import AnomalyResultBuilder


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def normalized_doc_setup(db_session: Session):
    """Create a fully normalized document with Agent 1 results."""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="test_result_doc.csv",
        file_type="csv",
        file_path="/tmp/test_result_doc.csv",
        status=DocumentStatus.NORMALIZED.value
    )
    db_session.add(doc)

    fin_data = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        company_name="Result Corp",
        currency="USD",
        fiscal_year="2023",
        revenue=10000000.0,
        assets=25000000.0,
        liabilities=10000000.0,
        equity=15000000.0,
        normalized_data={
            "company": {"name": "Result Corp", "currency": "USD"},
            "period": {"fiscal_year": "2023"},
            "financial_data": {
                "revenue": 10000000.0,
                "gross_profit": 4000000.0,
                "net_profit": 1500000.0,
                "assets": 25000000.0,
                "liabilities": 10000000.0,
                "equity": 15000000.0,
                "current_assets": 8000000.0,
                "current_liabilities": 4000000.0,
                "inventory": 2000000.0,
            },
            "validation": {
                "balance_sheet_check": {"status": "VALID", "is_valid": True}
            },
            "analysis": {
                "yoy": {"status": "COMPLETED"},
                "ratios": {
                    "status": "COMPLETED",
                    "ratios": {
                        "liquidity": {
                            "current_ratio": {"value": 2.0, "status": "COMPLETED"},
                            "quick_ratio": {"value": 1.5, "status": "COMPLETED"}
                        },
                        "profitability": {
                            "gross_profit_margin": {"value": 40.0, "status": "COMPLETED"},
                            "net_profit_margin": {"value": 15.0, "status": "COMPLETED"},
                            "return_on_assets": {"value": 6.0, "status": "COMPLETED"},
                            "return_on_equity": {"value": 10.0, "status": "COMPLETED"},
                        },
                        "leverage": {
                            "debt_to_equity": {"value": 0.6667, "status": "COMPLETED"},
                            "debt_ratio": {"value": 0.4, "status": "COMPLETED"}
                        }
                    }
                },
                "agent1": {
                    "status": "COMPLETED",
                    "results": {
                        "financial_ratios": {
                            "status": "COMPLETED",
                            "ratios": {
                                "liquidity": {
                                    "current_ratio": {"value": 2.0}
                                },
                                "profitability": {
                                    "gross_profit_margin": {"value": 40.0},
                                    "net_profit_margin": {"value": 15.0},
                                    "return_on_assets": {"value": 6.0},
                                    "return_on_equity": {"value": 10.0},
                                },
                                "leverage": {
                                    "debt_to_equity": {"value": 0.6667}
                                }
                            }
                        }
                    }
                }
            }
        }
    )
    db_session.add(fin_data)
    db_session.commit()

    return doc_id


# ====================================================================
# Unit Tests for AnomalyResultBuilder
# ====================================================================

def test_result_builder_normal_prediction():
    """1. Normal prediction (prediction = 1) -> classification = 'NORMAL'."""
    raw = {
        "status": "COMPLETED",
        "model": {"type": "IsolationForest", "version": "1.8.0", "training_dataset": "Financial Statements.csv", "feature_count": 6},
        "features": {"current_ratio": 2.0},
        "anomaly_detection": {
            "prediction": 1,
            "label": "normal",
            "is_anomaly": False,
            "score": 0.125591,
        },
        "warnings": [],
        "reason": None,
    }

    res = AnomalyResultBuilder.build_result("doc-123", raw)
    assert res["status"] == "COMPLETED"
    assert res["classification"] == "NORMAL"
    assert res["prediction"] == 1
    assert res["is_anomaly"] is False
    assert res["anomaly_score"] == 0.125591
    assert res["anomaly_detection"]["classification"] == "NORMAL"


def test_result_builder_anomaly_prediction():
    """2. Anomaly prediction (prediction = -1) -> classification = 'ANOMALY'."""
    raw = {
        "status": "COMPLETED",
        "model": {"type": "IsolationForest", "version": "1.8.0", "training_dataset": "Financial Statements.csv", "feature_count": 6},
        "features": {"current_ratio": 0.1},
        "anomaly_detection": {
            "prediction": -1,
            "label": "anomaly",
            "is_anomaly": True,
            "score": -0.145678,
        },
        "warnings": [],
        "reason": None,
    }

    res = AnomalyResultBuilder.build_result("doc-456", raw)
    assert res["status"] == "COMPLETED"
    assert res["classification"] == "ANOMALY"
    assert res["prediction"] == -1
    assert res["is_anomaly"] is True
    assert res["anomaly_score"] == -0.145678
    assert res["anomaly_detection"]["classification"] == "ANOMALY"


def test_result_builder_score_preservation():
    """3. Exact score precision preservation."""
    score = 0.089123
    raw = {
        "status": "COMPLETED",
        "model": {},
        "features": {},
        "anomaly_detection": {"prediction": 1, "score": score},
    }
    res = AnomalyResultBuilder.build_result("doc-score", raw)
    assert res["anomaly_score"] == score
    assert res["anomaly_detection"]["score"] == score


def test_result_builder_zero_score():
    """4. Zero score handled safely."""
    raw = {
        "status": "COMPLETED",
        "model": {},
        "features": {},
        "anomaly_detection": {"prediction": 1, "score": 0.0},
    }
    res = AnomalyResultBuilder.build_result("doc-zero", raw)
    assert res["anomaly_score"] == 0.0


def test_result_builder_positive_and_negative_scores():
    """5 & 6. Positive and negative score handling."""
    raw_pos = {"anomaly_detection": {"prediction": 1, "score": 0.15}}
    raw_neg = {"anomaly_detection": {"prediction": -1, "score": -0.12}}

    res_pos = AnomalyResultBuilder.build_result("doc-p", raw_pos)
    res_neg = AnomalyResultBuilder.build_result("doc-n", raw_neg)

    assert res_pos["anomaly_score"] == 0.15
    assert res_neg["anomaly_score"] == -0.12


def test_result_builder_large_finite_score():
    """7. Large finite score handled safely."""
    raw = {"anomaly_detection": {"prediction": 1, "score": 12345.6789}}
    res = AnomalyResultBuilder.build_result("doc-large", raw)
    assert res["anomaly_score"] == 12345.6789


def test_result_builder_missing_or_invalid_scores():
    """8, 9, 10. Missing, None, NaN, and Inf score rejection."""
    # Missing score
    with pytest.raises(ValueError, match="Missing, NaN, or non-finite anomaly score"):
        AnomalyResultBuilder.build_result("doc-m", {"anomaly_detection": {"prediction": 1}})

    # None score
    with pytest.raises(ValueError, match="Missing, NaN, or non-finite anomaly score"):
        AnomalyResultBuilder.build_result("doc-none", {"anomaly_detection": {"prediction": 1, "score": None}})

    # NaN score
    with pytest.raises(ValueError, match="Missing, NaN, or non-finite anomaly score"):
        AnomalyResultBuilder.build_result("doc-nan", {"anomaly_detection": {"prediction": 1, "score": float("nan")}})

    # Inf score
    with pytest.raises(ValueError, match="Missing, NaN, or non-finite anomaly score"):
        AnomalyResultBuilder.build_result("doc-inf", {"anomaly_detection": {"prediction": 1, "score": float("inf")}})


def test_result_builder_invalid_prediction():
    """11. Invalid prediction value rejected."""
    with pytest.raises(ValueError, match="Invalid ML prediction"):
        AnomalyResultBuilder.build_result("doc-p", {"anomaly_detection": {"prediction": 0, "score": 0.1}})

    with pytest.raises(ValueError, match="Invalid ML prediction"):
        AnomalyResultBuilder.build_result("doc-p2", {"anomaly_detection": {"prediction": 2, "score": 0.1}})


def test_result_builder_missing_anomaly_detection_block():
    """12. Missing anomaly_detection block raises ValueError."""
    with pytest.raises(ValueError, match="Missing or malformed 'anomaly_detection' block"):
        AnomalyResultBuilder.build_result("doc-missing-ad", {})


def test_result_builder_incomplete_status_and_warnings():
    """13, 14, 15. INCOMPLETE status, warning preservation, and metadata preservation."""
    raw = {
        "status": "INCOMPLETE",
        "model": {"type": "IsolationForest", "version": "1.8.0", "training_dataset": "Financial Statements.csv", "feature_count": 6},
        "features": {"current_ratio": 1.0},
        "anomaly_detection": {"prediction": 1, "score": 0.05},
        "warnings": ["Feature 'current_ratio' was unavailable; neutral baseline used."],
        "reason": "Analysis completed with imputed baselines.",
    }

    res = AnomalyResultBuilder.build_result("doc-inc", raw)
    assert res["status"] == "INCOMPLETE"
    assert len(res["warnings"]) == 1
    assert "current_ratio" in res["warnings"][0]
    assert res["reason"] == "Analysis completed with imputed baselines."
    assert res["model"]["type"] == "IsolationForest"


def test_result_builder_deterministic_repeated():
    """16. Deterministic repeated calls on identical input."""
    raw = {"anomaly_detection": {"prediction": 1, "score": 0.112233}}
    res1 = AnomalyResultBuilder.build_result("doc-rep", raw)
    res2 = AnomalyResultBuilder.build_result("doc-rep", raw)
    assert res1 == res2


def test_result_builder_json_serialization():
    """17. JSON serialization of final result."""
    raw = {
        "status": "COMPLETED",
        "model": {"type": "IsolationForest", "version": "1.8.0", "training_dataset": "Financial Statements.csv", "feature_count": 6},
        "features": {"current_ratio": 2.0, "debt_to_equity": 0.5},
        "anomaly_detection": {"prediction": 1, "score": 0.12},
        "warnings": [],
        "reason": None,
    }
    res = AnomalyResultBuilder.build_result("doc-json", raw)
    serialized = json.dumps(res)
    deserialized = json.loads(serialized)
    assert deserialized["classification"] == "NORMAL"
    assert deserialized["anomaly_score"] == 0.12


# ====================================================================
# Integration Tests via API Client
# ====================================================================

def test_api_anomaly_result_fields(client, normalized_doc_setup):
    """18. API returns top-level classification and anomaly_score fields."""
    doc_id = normalized_doc_setup
    resp = client.post(f"/api/v1/ml/{doc_id}/anomaly")
    assert resp.status_code == 200

    data = resp.json()
    assert "classification" in data
    assert data["classification"] in ("NORMAL", "ANOMALY")
    assert "anomaly_score" in data
    assert isinstance(data["anomaly_score"], float)
    assert "prediction" in data
    assert "is_anomaly" in data
    assert data["anomaly_detection"]["classification"] == data["classification"]
    assert data["anomaly_detection"]["anomaly_score"] == data["anomaly_score"]


def test_api_invalid_uuid(client):
    """19. API rejects invalid UUID."""
    resp = client.post("/api/v1/ml/bad-uuid-format/anomaly")
    assert resp.status_code == 400
    assert "Invalid document ID format" in resp.json()["detail"]


def test_api_nonexistent_document(client):
    """20. API rejects nonexistent document."""
    resp = client.post(f"/api/v1/ml/{uuid.uuid4()}/anomaly")
    assert resp.status_code == 404


def test_api_unnormalized_document(client, db_session):
    """21. API rejects unnormalized document."""
    unnorm_id = str(uuid.uuid4())
    doc = Document(
        id=unnorm_id,
        filename="unnorm.csv",
        file_type="csv",
        file_path="/tmp/unnorm.csv",
        status=DocumentStatus.UPLOADED.value
    )
    db_session.add(doc)
    db_session.commit()

    resp = client.post(f"/api/v1/ml/{unnorm_id}/anomaly")
    assert resp.status_code == 400
    assert "UPLOADED" in resp.json()["detail"]


def test_api_persistence_and_sibling_preservation(client, normalized_doc_setup, db_session):
    """22 & 23. Database persistence under ml_anomaly and sibling preservation."""
    doc_id = normalized_doc_setup
    resp = client.post(f"/api/v1/ml/{doc_id}/anomaly")
    assert resp.status_code == 200

    fin = db_session.query(FinancialData).filter(FinancialData.document_id == doc_id).first()
    db_session.refresh(fin)
    stored = fin.normalized_data

    assert "ml_anomaly" in stored
    assert stored["ml_anomaly"]["classification"] in ("NORMAL", "ANOMALY")
    assert "validation" in stored
    assert "yoy" in stored["analysis"]
    assert "ratios" in stored["analysis"]
    assert "agent1" in stored["analysis"]


def test_api_repeated_execution_idempotence(client, normalized_doc_setup, db_session):
    """24. Repeated API execution is idempotent."""
    doc_id = normalized_doc_setup
    r1 = client.post(f"/api/v1/ml/{doc_id}/anomaly")
    r2 = client.post(f"/api/v1/ml/{doc_id}/anomaly")

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["anomaly_score"] == r2.json()["anomaly_score"]
    assert r1.json()["classification"] == r2.json()["classification"]

    count = db_session.query(FinancialData).filter(FinancialData.document_id == doc_id).count()
    assert count == 1


def test_api_database_rollback_on_persistence_failure(client, normalized_doc_setup, db_session):
    """25. Database rollback if persistence fails."""
    doc_id = normalized_doc_setup

    def failing_db():
        db = SessionLocal()
        def fail():
            raise RuntimeError("Database commit error during ML result persistence")
        db.commit = fail
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = failing_db
    try:
        resp = client.post(f"/api/v1/ml/{doc_id}/anomaly")
        assert resp.status_code == 500
        assert "Failed to persist ML anomaly" in resp.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_db, None)

    # Verify original document unchanged
    fin = db_session.query(FinancialData).filter(FinancialData.document_id == doc_id).first()
    db_session.refresh(fin)
    assert "validation" in fin.normalized_data
    assert "agent1" in fin.normalized_data["analysis"]
