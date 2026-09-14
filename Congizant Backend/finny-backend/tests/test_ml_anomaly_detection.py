"""Comprehensive unit and integration tests for Step 3.3 ML Anomaly Detection inference."""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database.database import SessionLocal
from app.models.document import Document, DocumentStatus
from app.models.financial_data import FinancialData
from app.services.ml.anomaly_detector import AnomalyDetector
from app.services.ml.model_loader import ModelLoader


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
        filename="test_statement.csv",
        file_type="csv",
        file_path="/tmp/test.csv",
        status=DocumentStatus.NORMALIZED.value
    )
    db_session.add(doc)

    fin_data = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        company_name="Acme Corp",
        currency="USD",
        fiscal_year="2023",
        revenue=10000000.0,
        assets=25000000.0,
        liabilities=10000000.0,
        equity=15000000.0,
        normalized_data={
            "company": {"name": "Acme Corp", "currency": "USD"},
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


# 1. Unit Tests for AnomalyDetector Service
def test_detector_normal_agent1_data():
    """Verify inference on healthy/normal financial profile."""
    detector = AnomalyDetector()
    agent1_data = {
        "results": {
            "financial_ratios": {
                "ratios": {
                    "liquidity": {"current_ratio": {"value": 1.8}},
                    "leverage": {"debt_to_equity": {"value": 0.4}},
                    "profitability": {
                        "return_on_equity": {"value": 15.0},
                        "return_on_assets": {"value": 7.0},
                        "net_profit_margin": {"value": 12.0},
                        "gross_profit_margin": {"value": 45.0},
                    }
                }
            }
        }
    }

    res = detector.detect_anomalies(agent1_data, "test-id")
    assert res["status"] == "COMPLETED"
    assert res["model"]["type"] == "IsolationForest"
    assert res["anomaly_detection"]["prediction"] in (1, -1)
    assert isinstance(res["anomaly_detection"]["score"], float)
    assert not res["warnings"]


def test_detector_anomalous_agent1_data():
    """Verify extreme/unusual financial ratio profile."""
    detector = AnomalyDetector()
    agent1_data = {
        "results": {
            "financial_ratios": {
                "ratios": {
                    "liquidity": {"current_ratio": {"value": 0.1}},
                    "leverage": {"debt_to_equity": {"value": 25.0}},
                    "profitability": {
                        "return_on_equity": {"value": -85.0},
                        "return_on_assets": {"value": -30.0},
                        "net_profit_margin": {"value": -90.0},
                        "gross_profit_margin": {"value": 5.0},
                    }
                }
            }
        }
    }

    res = detector.detect_anomalies(agent1_data, "test-extreme")
    assert res["status"] == "COMPLETED"
    assert res["anomaly_detection"]["prediction"] == -1
    assert res["anomaly_detection"]["is_anomaly"] is True
    assert res["anomaly_detection"]["label"] == "anomaly"
    assert res["anomaly_detection"]["score"] < 0


def test_detector_deterministic_prediction():
    """Verify identical inputs produce identical anomaly score and label."""
    detector = AnomalyDetector()
    agent1_data = {
        "results": {
            "financial_ratios": {
                "ratios": {
                    "liquidity": {"current_ratio": {"value": 2.2}},
                    "leverage": {"debt_to_equity": {"value": 0.35}},
                    "profitability": {
                        "return_on_equity": {"value": 18.0},
                        "return_on_assets": {"value": 9.5},
                        "net_profit_margin": {"value": 16.0},
                        "gross_profit_margin": {"value": 52.0},
                    }
                }
            }
        }
    }

    res1 = detector.detect_anomalies(agent1_data, "test-id")
    res2 = detector.detect_anomalies(agent1_data, "test-id")
    assert res1["anomaly_detection"]["score"] == res2["anomaly_detection"]["score"]
    assert res1["anomaly_detection"]["prediction"] == res2["anomaly_detection"]["prediction"]


def test_detector_missing_ratio_handling():
    """Verify deterministic fallback when ratio is missing or None."""
    detector = AnomalyDetector()
    agent1_data = {
        "results": {
            "financial_ratios": {
                "ratios": {
                    "liquidity": {"current_ratio": {"value": None}},
                    "profitability": {
                        "gross_profit_margin": {"value": 35.0},
                    }
                }
            }
        }
    }

    res = detector.detect_anomalies(agent1_data, "test-missing")
    assert res["status"] == "INCOMPLETE"
    assert len(res["warnings"]) > 0
    assert "debt_to_equity" in res["reason"]


def test_detector_negative_and_large_values():
    """Verify negative and very large numeric values do not crash."""
    detector = AnomalyDetector()
    agent1_data = {
        "results": {
            "financial_ratios": {
                "ratios": {
                    "liquidity": {"current_ratio": {"value": 500.0}},
                    "leverage": {"debt_to_equity": {"value": -12.5}},
                    "profitability": {
                        "return_on_equity": {"value": 2500.0},
                        "return_on_assets": {"value": -45.0},
                        "net_profit_margin": {"value": -150.0},
                        "gross_profit_margin": {"value": 99.0},
                    }
                }
            }
        }
    }

    res = detector.detect_anomalies(agent1_data, "test-extreme-vals")
    assert res["status"] == "COMPLETED"
    assert res["anomaly_detection"]["prediction"] in (1, -1)


def test_detector_missing_model_files(tmp_path):
    """Verify FileNotFoundError when model path is invalid."""
    empty_loader = ModelLoader(model_dir=tmp_path)
    detector = AnomalyDetector(model_loader=empty_loader)
    with pytest.raises(FileNotFoundError, match="model artifacts are not available"):
        detector.detect_anomalies({}, "test-doc")


# 2. Integration Tests via FastAPI Client
def test_api_anomaly_success(client, normalized_doc_setup, db_session):
    """Verify successful POST /api/v1/ml/{document_id}/anomaly."""
    doc_id = normalized_doc_setup
    res = client.post(f"/api/v1/ml/{doc_id}/anomaly")
    assert res.status_code == 200

    body = res.json()
    assert body["document_id"] == doc_id
    assert body["status"] == "COMPLETED"
    assert body["model"]["type"] == "IsolationForest"
    assert "prediction" in body["anomaly_detection"]
    assert "score" in body["anomaly_detection"]
    assert "label" in body["anomaly_detection"]
    assert body["anomaly_detection"]["label"] in ("normal", "anomaly")

    # Verify database persistence under normalized_data['ml_anomaly']
    fin_record = db_session.query(FinancialData).filter(FinancialData.document_id == doc_id).first()
    db_session.refresh(fin_record)
    assert "ml_anomaly" in fin_record.normalized_data
    assert fin_record.normalized_data["ml_anomaly"]["anomaly_detection"]["prediction"] == body["anomaly_detection"]["prediction"]
    # Ensure sibling sections were preserved
    assert "validation" in fin_record.normalized_data
    assert "yoy" in fin_record.normalized_data["analysis"]
    assert "ratios" in fin_record.normalized_data["analysis"]
    assert "agent1" in fin_record.normalized_data["analysis"]


def test_api_anomaly_idempotence(client, normalized_doc_setup, db_session):
    """Verify repeated execution updates only ml_anomaly and preserves rows/data."""
    doc_id = normalized_doc_setup
    r1 = client.post(f"/api/v1/ml/{doc_id}/anomaly")
    r2 = client.post(f"/api/v1/ml/{doc_id}/anomaly")

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["anomaly_detection"]["score"] == r2.json()["anomaly_detection"]["score"]

    # Verify no duplicate rows
    count = db_session.query(FinancialData).filter(FinancialData.document_id == doc_id).count()
    assert count == 1

    # Verify document status remains NORMALIZED
    doc = db_session.query(Document).filter(Document.id == doc_id).first()
    assert doc.status == DocumentStatus.NORMALIZED.value


def test_api_anomaly_error_cases(client, db_session):
    """Verify error responses for invalid inputs."""
    # 1. Invalid UUID
    r_bad_uuid = client.post("/api/v1/ml/not-a-valid-uuid/anomaly")
    assert r_bad_uuid.status_code == 400
    assert "Invalid document ID format" in r_bad_uuid.json()["detail"]

    # 2. Nonexistent Document
    r_not_found = client.post(f"/api/v1/ml/{uuid.uuid4()}/anomaly")
    assert r_not_found.status_code == 404

    # 3. Unnormalized Document
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

    r_unnorm = client.post(f"/api/v1/ml/{unnorm_id}/anomaly")
    assert r_unnorm.status_code == 400
    assert "UPLOADED" in r_unnorm.json()["detail"]
