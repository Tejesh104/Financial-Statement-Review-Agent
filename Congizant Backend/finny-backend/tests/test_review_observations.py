"""Comprehensive tests for Step 4.2: Review Observations Layer."""

import json
import uuid
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.database import SessionLocal
from app.models.document import Document, DocumentStatus
from app.models.financial_data import FinancialData
from app.services.review.review_observations_builder import ReviewObservationsBuilder
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
def mock_ollama_client():
    mock_c = MagicMock()
    mock_c.model = "qwen2.5:7b"
    mock_c.generate_review.return_value = OllamaReviewContent(
        observations=[
            ObservationFinding(
                finding_type="VALIDATION",
                title="Balance Sheet Equality",
                finding="Balance sheet equation balances (Assets = Liabilities + Equity) within tolerance 0.01.",
                explanation="Verified balance holds across reported balance sheet schedule.",
                severity="LOW",
                evidence=[]
            ),
            ObservationFinding(
                finding_type="YOY",
                title="Revenue Expansion",
                finding="Revenue changed by +20.00% year-over-year (positive trend).",
                explanation="Top line sales increased reflecting sales volume expansion.",
                severity="LOW",
                evidence=[]
            )
        ],
        summary="Company displays balanced accounting records and positive top-line growth.",
        limitations=[]
    )
    return mock_c


# ==============================================================================
# 1. DETERMINISTIC SEVERITY & BASIC OBSERVATIONS TESTS
# ==============================================================================

def test_severity_rules_deterministic():
    # Math validation
    assert ReviewObservationsBuilder.determine_severity("VALIDATION", "INVALID") == "CRITICAL"
    assert ReviewObservationsBuilder.determine_severity("VALIDATION", "INCOMPLETE") == "MEDIUM"
    assert ReviewObservationsBuilder.determine_severity("VALIDATION", "VALID") == "LOW"

    # ML Anomaly
    assert ReviewObservationsBuilder.determine_severity("ML_ANOMALY", "ANOMALY", {"is_anomaly": True}) == "HIGH"
    assert ReviewObservationsBuilder.determine_severity("ML_ANOMALY", "NORMAL", {"is_anomaly": False}) == "LOW"

    # YoY
    assert ReviewObservationsBuilder.determine_severity("YOY", "COMPLETED", {"direction": "negative"}) == "MEDIUM"
    assert ReviewObservationsBuilder.determine_severity("YOY", "COMPLETED", {"direction": "positive"}) == "LOW"
    assert ReviewObservationsBuilder.determine_severity("YOY", "INSUFFICIENT_DATA") == "MEDIUM"

    # Ratio
    assert ReviewObservationsBuilder.determine_severity("RATIO", "UNDEFINED") == "MEDIUM"
    assert ReviewObservationsBuilder.determine_severity("RATIO", "INCOMPLETE") == "MEDIUM"
    assert ReviewObservationsBuilder.determine_severity("RATIO", "COMPLETED") == "LOW"


def test_build_observations_complete_valid_findings(mock_ollama_client):
    doc_id = str(uuid.uuid4())
    findings_data = {
        "status": "COMPLETED",
        "findings": {
            "validations": [{
                "type": "BALANCE_SHEET_VALIDATION",
                "status": "VALID",
                "difference": 0.0,
                "tolerance": 0.01,
            }],
            "variances": [{
                "field": "revenue",
                "current_value": 1200000.0,
                "previous_value": 1000000.0,
                "percentage_change": 20.0,
                "direction": "positive",
                "status": "COMPLETED",
            }],
            "anomalies": [{
                "classification": "NORMAL",
                "is_anomaly": False,
                "anomaly_score": 0.05,
                "status": "COMPLETED",
            }],
            "ratios": [{
                "name": "current_ratio",
                "category": "liquidity",
                "value": 2.0,
                "status": "COMPLETED",
            }],
            "evidence": [
                {"field": "revenue", "value": 1200000.0, "is_available": True},
                {"field": "assets", "value": 2400000.0, "is_available": True},
            ]
        }
    }

    res = ReviewObservationsBuilder.build_observations(
        document_id=doc_id,
        findings_data=findings_data,
        ollama_client=mock_ollama_client,
    )
    assert res["document_id"] == doc_id
    assert res["status"] == "COMPLETED"
    assert len(res["observations"]) >= 3
    for obs in res["observations"]:
        assert obs["finding"]
        assert obs["explanation"]
        assert obs["severity"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        assert len(obs["evidence"]) >= 1
        assert obs["recommendation"]


def test_build_observations_invalid_validation_critical(mock_ollama_client):
    doc_id = str(uuid.uuid4())
    findings_data = {
        "status": "PARTIAL",
        "findings": {
            "validations": [{
                "type": "BALANCE_SHEET_VALIDATION",
                "status": "INVALID",
                "difference": 250000.0,
                "tolerance": 0.01,
            }]
        }
    }
    res = ReviewObservationsBuilder.build_observations(
        document_id=doc_id,
        findings_data=findings_data,
        ollama_client=mock_ollama_client,
    )
    val_obs = [o for o in res["observations"] if "balance sheet" in o["finding"].lower()][0]
    assert val_obs["severity"] == "CRITICAL"
    assert "250,000.00" in val_obs["finding"]
    assert "balance-sheet inconsistency" in val_obs["recommendation"].lower()


def test_build_observations_ml_anomaly_high(mock_ollama_client):
    doc_id = str(uuid.uuid4())
    findings_data = {
        "status": "PARTIAL",
        "findings": {
            "anomalies": [{
                "classification": "ANOMALY",
                "is_anomaly": True,
                "anomaly_score": -0.185,
                "status": "COMPLETED",
            }]
        }
    }
    res = ReviewObservationsBuilder.build_observations(
        document_id=doc_id,
        findings_data=findings_data,
        ollama_client=mock_ollama_client,
    )
    ml_obs = [o for o in res["observations"] if "isolation forest" in o["finding"].lower()][0]
    assert ml_obs["severity"] == "HIGH"
    assert "-0.1850" in ml_obs["finding"]
    assert "statistically unusual" in ml_obs["recommendation"].lower()


# ==============================================================================
# 2. GROUNDING & ADVICE NEUTRALIZATION TESTS
# ==============================================================================

def test_grounding_block_investment_advice():
    mock_c = MagicMock()
    mock_c.model = "qwen2.5:7b"
    mock_c.generate_review.return_value = OllamaReviewContent(
        observations=[
            ObservationFinding(
                finding_type="YOY",
                title="Investment Recommendation",
                finding="Revenue grew strongly.",
                explanation="Buy this stock immediately for guaranteed returns.",
                severity="HIGH",
                evidence=[]
            )
        ],
        summary="Buy this stock now.",
        limitations=[]
    )

    findings_data = {
        "status": "COMPLETED",
        "findings": {
            "variances": [{
                "field": "revenue",
                "current_value": 500.0,
                "previous_value": 400.0,
                "percentage_change": 25.0,
                "direction": "positive",
                "status": "COMPLETED",
            }]
        }
    }

    res = ReviewObservationsBuilder.build_observations("doc-1", findings_data, ollama_client=mock_c)
    obs = res["observations"][0]
    assert "do not provide investment advice" in obs["explanation"].lower() or "sanitized" in obs["explanation"].lower()
    assert "buy this stock" not in obs["recommendation"].lower()


def test_grounding_numerical_immutability():
    """Verified evidence values must never be changed by Ollama output."""
    mock_c = MagicMock()
    mock_c.model = "qwen2.5:7b"
    mock_c.generate_review.return_value = OllamaReviewContent(
        observations=[
            ObservationFinding(
                finding_type="YOY",
                title="Hallucinated revenue",
                finding="Revenue was 999999999",
                explanation="Hallucinated number",
                severity="LOW",
                evidence=[]
            )
        ],
        summary="Hallucinated summary",
        limitations=[]
    )

    findings_data = {
        "status": "COMPLETED",
        "findings": {
            "variances": [{
                "field": "revenue",
                "current_value": 1500000.0,
                "previous_value": 1000000.0,
                "percentage_change": 50.0,
                "direction": "positive",
                "status": "COMPLETED",
            }]
        }
    }

    res = ReviewObservationsBuilder.build_observations("doc-2", findings_data, ollama_client=mock_c)
    ev_item = res["observations"][0]["evidence"][0]
    assert ev_item["current_value"] == 1500000.0
    assert ev_item["previous_value"] == 1000000.0


# ==============================================================================
# 3. API INTEGRATION & DATABASE PERSISTENCE TESTS
# ==============================================================================

def test_api_observations_invalid_uuid(client):
    res = client.post("/api/v1/agent2/bad-uuid/observations")
    assert res.status_code == 400
    assert "Expected a valid UUID" in res.json()["detail"]


def test_api_observations_nonexistent_doc(client):
    rand_id = str(uuid.uuid4())
    res = client.post(f"/api/v1/agent2/{rand_id}/observations")
    assert res.status_code == 404
    assert f"Document with ID '{rand_id}' not found" in res.json()["detail"]


def test_api_observations_unnormalized_doc(client, db_session):
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

    res = client.post(f"/api/v1/agent2/{doc_id}/observations")
    assert res.status_code == 400
    assert "has not been normalized yet" in res.json()["detail"]


def test_api_observations_success_with_persistence(client, db_session, mock_ollama_client):
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="obs_test.pdf",
        file_type="pdf",
        file_path="uploads/obs_test.pdf",
        status=DocumentStatus.NORMALIZED.value,
    )
    db_session.add(doc)

    fin_data = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        company_name="Observations Co",
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

    with patch("app.services.review.review_observations_builder.OllamaClient", return_value=mock_ollama_client):
        res = client.post(f"/api/v1/agent2/{doc_id}/observations")
        assert res.status_code == 200
        payload = res.json()
        assert payload["document_id"] == doc_id
        assert payload["status"] in ("COMPLETED", "PARTIAL")
        assert len(payload["observations"]) >= 1

        # Check DB persistence under normalized_data['review_observations']
        db_session.expire_all()
        rec = db_session.query(FinancialData).filter(FinancialData.document_id == doc_id).first()
        norm = rec.normalized_data
        assert "review_observations" in norm
        assert len(norm["review_observations"]["observations"]) >= 1
        # Check sibling sections preserved
        assert "financial_data" in norm
        assert "analysis" in norm


def test_api_observations_idempotency(client, db_session, mock_ollama_client):
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="idem_obs.pdf",
        file_type="pdf",
        file_path="uploads/idem_obs.pdf",
        status=DocumentStatus.NORMALIZED.value,
    )
    db_session.add(doc)

    fin_data = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        normalized_data={"financial_data": {"revenue": 500000.0}}
    )
    db_session.add(fin_data)
    db_session.commit()

    with patch("app.services.review.review_observations_builder.OllamaClient", return_value=mock_ollama_client):
        res1 = client.post(f"/api/v1/agent2/{doc_id}/observations")
        assert res1.status_code == 200
        res2 = client.post(f"/api/v1/agent2/{doc_id}/observations")
        assert res2.status_code == 200

    # Ensure single FinancialData record maintained
    count = db_session.query(FinancialData).filter(FinancialData.document_id == doc_id).count()
    assert count == 1


def test_api_observations_rollback_on_db_error(client, db_session, mock_ollama_client, monkeypatch):
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="err_obs.pdf",
        file_type="pdf",
        file_path="uploads/err_obs.pdf",
        status=DocumentStatus.NORMALIZED.value,
    )
    db_session.add(doc)
    fin_data = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        normalized_data={"financial_data": {"revenue": 500000.0}}
    )
    db_session.add(fin_data)
    db_session.commit()

    from sqlalchemy.orm import Session
    def mock_commit(self):
        raise RuntimeError("Simulated DB failure")

    monkeypatch.setattr(Session, "commit", mock_commit)

    with patch("app.services.review.review_observations_builder.OllamaClient", return_value=mock_ollama_client):
        res = client.post(f"/api/v1/agent2/{doc_id}/observations")
        assert res.status_code == 500
        assert "failed to persist" in res.json()["detail"].lower()


def test_api_observations_ollama_unavailable_503(client, db_session):
    from app.services.agent2.ollama_client import OllamaUnavailableException
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="unav_obs.pdf",
        file_type="pdf",
        file_path="uploads/unav_obs.pdf",
        status=DocumentStatus.NORMALIZED.value,
    )
    db_session.add(doc)
    fin_data = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        normalized_data={"financial_data": {"revenue": 500000.0}}
    )
    db_session.add(fin_data)
    db_session.commit()

    with patch("app.services.agent2.ollama_client.OllamaClient.generate_review", side_effect=OllamaUnavailableException("Connection refused")):
        res = client.post(f"/api/v1/agent2/{doc_id}/observations")
        assert res.status_code == 503
        assert "unavailable" in res.json()["detail"].lower()


def test_api_observations_ollama_timeout_504(client, db_session):
    from app.services.agent2.ollama_client import OllamaTimeoutException
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="to_obs.pdf",
        file_type="pdf",
        file_path="uploads/to_obs.pdf",
        status=DocumentStatus.NORMALIZED.value,
    )
    db_session.add(doc)
    fin_data = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        normalized_data={"financial_data": {"revenue": 500000.0}}
    )
    db_session.add(fin_data)
    db_session.commit()

    with patch("app.services.agent2.ollama_client.OllamaClient.generate_review", side_effect=OllamaTimeoutException("Timed out")):
        res = client.post(f"/api/v1/agent2/{doc_id}/observations")
        assert res.status_code == 504
        assert "timed out" in res.json()["detail"].lower()


def test_api_observations_ollama_malformed_502(client, db_session):
    from app.services.agent2.ollama_client import OllamaMalformedResponseException
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="mal_obs.pdf",
        file_type="pdf",
        file_path="uploads/mal_obs.pdf",
        status=DocumentStatus.NORMALIZED.value,
    )
    db_session.add(doc)
    fin_data = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        normalized_data={"financial_data": {"revenue": 500000.0}}
    )
    db_session.add(fin_data)
    db_session.commit()

    with patch("app.services.agent2.ollama_client.OllamaClient.generate_review", side_effect=OllamaMalformedResponseException("Invalid JSON")):
        res = client.post(f"/api/v1/agent2/{doc_id}/observations")
        assert res.status_code == 502
        assert "malformed" in res.json()["detail"].lower()


def test_build_observations_undefined_and_incomplete_ratios(mock_ollama_client):
    doc_id = str(uuid.uuid4())
    findings_data = {
        "status": "PARTIAL",
        "findings": {
            "ratios": [
                {"name": "quick_ratio", "category": "liquidity", "status": "UNDEFINED", "value": None},
                {"name": "debt_to_equity", "category": "leverage", "status": "INCOMPLETE", "value": None},
            ]
        }
    }
    res = ReviewObservationsBuilder.build_observations(doc_id, findings_data, ollama_client=mock_ollama_client)
    severities = [o["severity"] for o in res["observations"]]
    assert "MEDIUM" in severities


def test_build_observations_negative_variance_and_nan_safety(mock_ollama_client):
    doc_id = str(uuid.uuid4())
    findings_data = {
        "status": "COMPLETED",
        "findings": {
            "variances": [
                {
                    "field": "net_profit",
                    "current_value": -50000.0,
                    "previous_value": 100000.0,
                    "percentage_change": -150.0,
                    "direction": "negative",
                    "status": "COMPLETED"
                }
            ],
            "evidence": [
                {"field": "net_profit", "value": float("nan"), "is_available": True}
            ]
        }
    }
    res = ReviewObservationsBuilder.build_observations(doc_id, findings_data, ollama_client=mock_ollama_client)
    obs = res["observations"][0]
    assert obs["severity"] == "MEDIUM"
    assert obs["evidence"][0]["value"] == -50000.0


def test_grounding_fraud_allegation_sanitized(mock_ollama_client):
    mock_c = MagicMock()
    mock_c.model = "qwen2.5:7b"
    mock_c.generate_review.return_value = OllamaReviewContent(
        observations=[
            ObservationFinding(
                finding_type="ML_ANOMALY",
                title="Allegation",
                finding="Isolation Forest flagged anomaly.",
                explanation="This company is involved in criminal fraud and money manipulation.",
                severity="HIGH",
                evidence=[]
            )
        ],
        summary="Criminal fraud detected.",
        limitations=[]
    )
    findings_data = {
        "status": "COMPLETED",
        "findings": {
            "anomalies": [{"classification": "ANOMALY", "is_anomaly": True, "anomaly_score": -0.2}]
        }
    }
    res = ReviewObservationsBuilder.build_observations("doc-fraud", findings_data, ollama_client=mock_c)
    assert "sanitized" in res["observations"][0]["explanation"].lower()


def test_live_ollama_review_observations(client, db_session):
    """Real live Ollama test: invokes local qwen2.5:7b model if online."""
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
        filename="live_obs.pdf",
        file_type="pdf",
        file_path="uploads/live_obs.pdf",
        status=DocumentStatus.NORMALIZED.value,
    )
    db_session.add(doc)
    fin_data = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        company_name="Live Review Co",
        fiscal_year="2024",
        revenue=2000000.0,
        assets=4000000.0,
        liabilities=1500000.0,
        equity=2500000.0,
        normalized_data={
            "financial_data": {
                "revenue": 2000000.0,
                "gross_profit": 800000.0,
                "net_profit": 300000.0,
                "assets": 4000000.0,
                "liabilities": 1500000.0,
                "equity": 2500000.0,
                "current_assets": 1200000.0,
                "current_liabilities": 600000.0,
                "inventory": 150000.0,
            }
        }
    )
    db_session.add(fin_data)
    db_session.commit()

    res = client.post(f"/api/v1/agent2/{doc_id}/observations")
    if res.status_code == 504:
        pytest.skip("Local Ollama timed out due to CPU load during test run")
    assert res.status_code == 200
    payload = res.json()
    assert payload["status"] in ("COMPLETED", "PARTIAL")
    assert len(payload["observations"]) >= 1
    assert payload["model"] == "qwen2.5:7b"
