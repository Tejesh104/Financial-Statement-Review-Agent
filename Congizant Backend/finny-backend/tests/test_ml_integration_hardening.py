"""Targeted integration hardening, artifact corruption, numerical safety, and security tests for Step 3.4."""

import uuid
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database.database import SessionLocal, get_db
from app.models.document import Document, DocumentStatus
from app.models.financial_data import FinancialData
from app.services.ml.feature_schema import ML_FEATURE_NAMES
from app.services.ml.model_loader import ModelLoader
from app.services.ml.anomaly_detector import AnomalyDetector


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
def populated_doc(db_session: Session):
    """Fixture creating a fully processed document with all Stage 1 and Stage 2 sections."""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="hardening_statement.csv",
        file_type="csv",
        file_path="/tmp/hardening_statement.csv",
        status=DocumentStatus.NORMALIZED.value
    )
    db_session.add(doc)

    fin = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        company_name="Hardening Corp",
        currency="USD",
        fiscal_year="2023",
        revenue=50000000.0,
        assets=100000000.0,
        liabilities=40000000.0,
        equity=60000000.0,
        normalized_data={
            "company": {"name": "Hardening Corp", "currency": "USD"},
            "period": {"fiscal_year": "2023"},
            "financial_data": {
                "revenue": 50000000.0,
                "gross_profit": 20000000.0,
                "net_profit": 8000000.0,
                "assets": 100000000.0,
                "liabilities": 40000000.0,
                "equity": 60000000.0,
                "current_assets": 35000000.0,
                "current_liabilities": 17500000.0,
                "inventory": 7000000.0,
            },
            "validation": {
                "balance_sheet_check": {"status": "VALID", "is_valid": True, "difference": 0.0}
            },
            "analysis": {
                "yoy": {"status": "COMPLETED", "periods": {"previous": "2022", "current": "2023"}},
                "ratios": {
                    "status": "COMPLETED",
                    "ratios": {
                        "liquidity": {
                            "current_ratio": {"value": 2.0, "status": "COMPLETED"},
                            "quick_ratio": {"value": 1.6, "status": "COMPLETED"}
                        },
                        "profitability": {
                            "gross_profit_margin": {"value": 40.0, "status": "COMPLETED"},
                            "net_profit_margin": {"value": 16.0, "status": "COMPLETED"},
                            "return_on_assets": {"value": 8.0, "status": "COMPLETED"},
                            "return_on_equity": {"value": 13.33, "status": "COMPLETED"},
                        },
                        "leverage": {
                            "debt_to_equity": {"value": 0.6667, "status": "COMPLETED"},
                            "debt_ratio": {"value": 0.4, "status": "COMPLETED"}
                        }
                    }
                },
                "agent1": {
                    "agent": "Agent 1",
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
                                    "net_profit_margin": {"value": 16.0},
                                    "return_on_assets": {"value": 8.0},
                                    "return_on_equity": {"value": 13.33},
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
    db_session.add(fin)
    db_session.commit()
    return doc_id


# ====================================================================
# 1. Model Artifact Failure & Corruption Handling
# ====================================================================

def test_missing_model_file_handling(tmp_path):
    """Verify ModelLoader and API handle missing joblib model file gracefully."""
    # Write only schema and metadata, omitting isolation_forest.joblib
    (tmp_path / "feature_schema.json").write_text("{}", encoding="utf-8")
    (tmp_path / "model_metadata.json").write_text("{}", encoding="utf-8")

    loader = ModelLoader(model_dir=tmp_path)
    assert loader.is_model_available() is False
    with pytest.raises(FileNotFoundError, match="Model artifacts not found"):
        loader.load()


def test_corrupted_joblib_file_handling(tmp_path):
    """Verify ModelLoader handles a corrupted or non-joblib binary gracefully."""
    (tmp_path / "isolation_forest.joblib").write_text("not a joblib file", encoding="utf-8")
    (tmp_path / "feature_schema.json").write_text("{}", encoding="utf-8")
    (tmp_path / "model_metadata.json").write_text(
        json.dumps({"feature_names": ML_FEATURE_NAMES}), encoding="utf-8"
    )

    loader = ModelLoader(model_dir=tmp_path)
    assert loader.is_model_available() is True
    with pytest.raises(ValueError, match="Corrupted or invalid model file"):
        loader.load()


def test_corrupted_metadata_json_handling(tmp_path):
    """Verify ModelLoader handles malformed JSON in metadata file."""
    (tmp_path / "isolation_forest.joblib").write_bytes(b"dummy")
    (tmp_path / "feature_schema.json").write_text("{}", encoding="utf-8")
    (tmp_path / "model_metadata.json").write_text("{bad json: true,", encoding="utf-8")

    loader = ModelLoader(model_dir=tmp_path)
    with patch("joblib.load", return_value=MagicMock()):
        with pytest.raises(ValueError, match="Corrupted or invalid model metadata JSON"):
            loader.load()



def test_feature_order_or_count_mismatch(tmp_path):
    """Verify ModelLoader rejects metadata with wrong feature order or count."""
    (tmp_path / "isolation_forest.joblib").write_bytes(b"dummy")
    (tmp_path / "feature_schema.json").write_text("{}", encoding="utf-8")
    # Reverse feature order
    reversed_features = list(reversed(ML_FEATURE_NAMES))
    (tmp_path / "model_metadata.json").write_text(
        json.dumps({"feature_names": reversed_features}), encoding="utf-8"
    )

    loader = ModelLoader(model_dir=tmp_path)
    # Patch joblib.load to avoid unpickling error
    with patch("joblib.load", return_value=MagicMock()):
        with pytest.raises(ValueError, match="Feature schema mismatch"):
            loader.load()


# ====================================================================
# 2. Numerical Robustness & Boundary Conditions
# ====================================================================

def test_numerical_safety_zero_division_undefined_ratios():
    """Verify that undefined Agent 1 ratios (e.g., zero denominator) use documented neutral imputation with warning."""
    detector = AnomalyDetector()
    # Ratios with None / undefined values from zero denominators
    agent1_zero_denoms = {
        "results": {
            "financial_ratios": {
                "ratios": {
                    "liquidity": {"current_ratio": {"value": None, "status": "UNDEFINED"}},
                    "leverage": {"debt_to_equity": {"value": None, "status": "UNDEFINED"}},
                    "profitability": {
                        "gross_profit_margin": {"value": None, "status": "UNDEFINED"},
                        "net_profit_margin": {"value": 15.0},
                        "return_on_assets": {"value": 5.0},
                        "return_on_equity": {"value": 10.0},
                    }
                }
            }
        }
    }

    res = detector.detect_anomalies(agent1_zero_denoms, "doc-undefined")
    assert res["status"] == "INCOMPLETE"
    assert len(res["warnings"]) == 3
    assert res["anomaly_detection"]["prediction"] in (1, -1)
    assert not math_is_nan_or_inf(res["anomaly_detection"]["score"])


def test_numerical_safety_malformed_types_in_agent1():
    """Verify that non-numeric types (e.g. strings, dictionaries) inside ratio values don't crash detector."""
    detector = AnomalyDetector()
    agent1_malformed = {
        "results": {
            "financial_ratios": {
                "ratios": {
                    "liquidity": {"current_ratio": {"value": "not-a-number"}},
                    "leverage": {"debt_to_equity": {"value": {"nested": "error"}}},
                    "profitability": {
                        "gross_profit_margin": {"value": None},
                        "net_profit_margin": {"value": float("nan")},
                        "return_on_assets": {"value": float("inf")},
                        "return_on_equity": {"value": 10.0},
                    }
                }
            }
        }
    }

    res = detector.detect_anomalies(agent1_malformed, "doc-malformed")
    assert res["status"] == "INCOMPLETE"
    # Unparseable inputs are safely converted to None and imputed with neutral baselines + warnings
    assert len(res["warnings"]) == 5
    assert not math_is_nan_or_inf(res["anomaly_detection"]["score"])


def math_is_nan_or_inf(val: float) -> bool:
    import math
    return math.isnan(val) or math.isinf(val)


# ====================================================================
# 3. Document Lifecycle State Enforcement
# ====================================================================

@pytest.mark.parametrize("invalid_state", [
    DocumentStatus.UPLOADED.value,
    DocumentStatus.EXTRACTING.value,
    DocumentStatus.EXTRACTED.value,
    DocumentStatus.NORMALIZING.value,
    DocumentStatus.EXTRACTION_FAILED.value,
    DocumentStatus.NORMALIZATION_FAILED.value,
])
def test_api_rejects_unnormalized_document_states(client, db_session, invalid_state):
    """Verify POST /api/v1/ml/{document_id}/anomaly rejects all unnormalized document states with HTTP 400."""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="unnormalized.csv",
        file_type="csv",
        file_path="/tmp/test.csv",
        status=invalid_state
    )
    db_session.add(doc)
    db_session.commit()

    resp = client.post(f"/api/v1/ml/{doc_id}/anomaly")
    assert resp.status_code == 400
    assert invalid_state in resp.json()["detail"]


# ====================================================================
# 4. Database Rollback on Persistence Failure
# ====================================================================

def test_database_rollback_on_commit_failure(client, populated_doc, db_session):
    """Verify that if db.commit() fails during ML persistence, changes are rolled back and HTTP 500 returned."""
    doc_id = populated_doc

    # Get snapshot of normalized_data before failed call
    fin_before = db_session.query(FinancialData).filter(FinancialData.document_id == doc_id).first()
    db_session.refresh(fin_before)
    snapshot_data = dict(fin_before.normalized_data or {})

    # Create a wrapper dependency that injects commit failure
    def get_db_with_commit_failure():
        db = SessionLocal()
        orig_commit = db.commit
        def failing_commit():
            raise RuntimeError("Injected database disk failure during ML persistence")
        db.commit = failing_commit
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = get_db_with_commit_failure
    try:
        resp = client.post(f"/api/v1/ml/{doc_id}/anomaly")
        assert resp.status_code == 500
        assert "Failed to persist ML anomaly" in resp.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_db, None)

    # Verify database was NOT partially modified
    fin_after = db_session.query(FinancialData).filter(FinancialData.document_id == doc_id).first()
    db_session.refresh(fin_after)
    # Existing analysis sections must be completely intact
    assert "validation" in fin_after.normalized_data
    assert "yoy" in fin_after.normalized_data["analysis"]
    assert "ratios" in fin_after.normalized_data["analysis"]
    assert "agent1" in fin_after.normalized_data["analysis"]
    # ml_anomaly should NOT be present
    assert "ml_anomaly" not in fin_after.normalized_data


# ====================================================================
# 5. Precedence of Explicit Debt over Total Liabilities
# ====================================================================

def test_explicit_debt_precedence_in_ml_pipeline(client, db_session):
    """Verify that explicit debt is used by Agent 1 and consumed by ML without overwriting with liabilities."""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="debt_test.csv",
        file_type="csv",
        file_path="/tmp/debt_test.csv",
        status=DocumentStatus.NORMALIZED.value
    )
    db_session.add(doc)

    # Liabilities = 50M, but explicit debt = 10M, Equity = 20M
    # If explicit debt is respected, Debt/Equity = 10M / 20M = 0.5
    # If liabilities overwrote debt, Debt/Equity would be 50M / 20M = 2.5
    fin = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        company_name="Debt Test Corp",
        currency="USD",
        fiscal_year="2023",
        revenue=30000000.0,
        assets=70000000.0,
        liabilities=50000000.0,
        equity=20000000.0,
        normalized_data={
            "company": {"name": "Debt Test Corp", "currency": "USD"},
            "period": {"fiscal_year": "2023"},
            "financial_data": {
                "revenue": 30000000.0,
                "gross_profit": 12000000.0,
                "net_profit": 3000000.0,
                "assets": 70000000.0,
                "liabilities": 50000000.0,
                "debt": 10000000.0,  # Explicit debt!
                "equity": 20000000.0,
                "current_assets": 25000000.0,
                "current_liabilities": 15000000.0,
            }
        }
    )
    db_session.add(fin)
    db_session.commit()

    # Call ML endpoint (which auto-computes Agent 1)
    resp = client.post(f"/api/v1/ml/{doc_id}/anomaly")
    assert resp.status_code == 200
    features = resp.json()["features"]

    # Must be 10M / 20M = 0.5, NOT 50M / 20M = 2.5
    assert features["debt_to_equity"] == 0.5
