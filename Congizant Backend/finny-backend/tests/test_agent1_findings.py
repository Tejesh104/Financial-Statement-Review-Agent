"""Tests for Step 3.6 — Agent 1 Findings Layer.

Verifies:
- Consolidation of validations, variances, anomalies, ratios, and evidence
- Status resolution (COMPLETED vs PARTIAL)
- Traceable evidence mapping
- Deduplicated warning propagation
- Zero recalculation
- JSON compliance (no NaN/Inf)
- Database persistence and atomicity under normalized_data['analysis']['agent1_findings']
- API routing, status codes (200, 400, 404), and error handling
"""

import math
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.database import SessionLocal
from app.models.document import Document, DocumentStatus
from app.models.financial_data import FinancialData
from app.services.agent1.findings_builder import FindingsBuilder
from app.schemas.findings import Agent1FindingsResponse


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


# ==============================================================================
# 1. UNIT TESTS — FINDINGS BUILDER
# ==============================================================================

def test_findings_unit_complete_dataset():
    """Test 1: Complete dataset produces all 5 sections with COMPLETED status."""
    doc_id = str(uuid.uuid4())
    norm_data = {
        "financial_data": {
            "revenue": 1000.0,
            "assets": 2000.0,
            "liabilities": 800.0,
            "equity": 1200.0,
            "current_assets": 600.0,
            "current_liabilities": 300.0,
            "inventory": 100.0,
            "gross_profit": 400.0,
            "net_profit": 150.0,
        },
        "validation": {
            "balance_sheet_check": {
                "status": "VALID",
                "is_valid": True,
                "difference": 0.0,
                "tolerance": 0.01,
                "reason": None,
            }
        },
        "analysis": {
            "yoy": {
                "status": "COMPLETED",
                "periods": {"current_period": "2024", "previous_period": "2023"},
                "financial_data": {
                    "revenue": {
                        "current": 1000.0,
                        "previous": 800.0,
                        "absolute_change": 200.0,
                        "percentage_change": 25.0,
                        "direction": "positive",
                        "status": "COMPLETED",
                        "reason": None,
                    }
                },
                "warnings": [],
                "reason": None,
            },
            "ratios": {
                "status": "COMPLETED",
                "ratios": {
                    "liquidity": {
                        "current_ratio": {"value": 2.0, "status": "COMPLETED", "reason": None}
                    },
                    "profitability": {
                        "net_profit_margin": {"value": 15.0, "status": "COMPLETED", "reason": None}
                    },
                    "leverage": {
                        "debt_to_equity": {"value": 0.67, "status": "COMPLETED", "reason": None}
                    }
                },
                "warnings": [],
                "reason": None,
            }
        },
        "ml_anomaly": {
            "is_anomaly": False,
            "score": -0.05,
            "prediction": 1,
            "label": "NORMAL",
            "status": "COMPLETED",
            "model": {"type": "IsolationForest"},
            "warnings": [],
            "reason": None,
        }
    }

    result = FindingsBuilder.build_findings(doc_id, norm_data)
    assert result["document_id"] == doc_id
    assert result["status"] == "COMPLETED"
    assert result["reason"] is None
    
    findings = result["findings"]
    assert len(findings["validations"]) == 1
    assert findings["validations"][0]["status"] == "VALID"
    assert findings["validations"][0]["is_valid"] is True
    
    assert len(findings["variances"]) == 1
    assert findings["variances"][0]["field"] == "revenue"
    assert findings["variances"][0]["percentage_change"] == 25.0
    
    assert len(findings["anomalies"]) == 1
    assert findings["anomalies"][0]["classification"] == "NORMAL"
    assert findings["anomalies"][0]["is_anomaly"] is False
    assert findings["anomalies"][0]["anomaly_score"] == -0.05
    
    assert len(findings["ratios"]) == 3
    assert len(findings["evidence"]) >= 9
    
    # Check schema validation passes
    pydantic_res = Agent1FindingsResponse(**result)
    assert pydantic_res.status == "COMPLETED"


def test_findings_unit_imbalanced_validation():
    """Test 2: Imbalanced balance sheet produces INVALID validation and PARTIAL status."""
    doc_id = str(uuid.uuid4())
    norm_data = {
        "financial_data": {"assets": 2000.0, "liabilities": 800.0, "equity": 1000.0},
        "validation": {
            "balance_sheet_check": {
                "status": "INVALID",
                "is_valid": False,
                "difference": 200.0,
                "tolerance": 0.01,
                "reason": "Assets (2000.0) != Liabilities + Equity (1800.0)",
            }
        },
        "analysis": {
            "yoy": {"status": "COMPLETED", "financial_data": {}},
            "ratios": {"status": "COMPLETED", "ratios": {}},
        },
        "ml_anomaly": {"is_anomaly": False, "score": -0.02, "prediction": 1, "label": "NORMAL"},
    }
    result = FindingsBuilder.build_findings(doc_id, norm_data)
    assert result["status"] == "PARTIAL"
    assert any("validation:" in w for w in result["warnings"])
    assert result["findings"]["validations"][0]["is_valid"] is False
    assert result["findings"]["validations"][0]["difference"] == 200.0


def test_findings_unit_missing_validation():
    """Test 3: Missing validation defaults to INCOMPLETE and PARTIAL status."""
    doc_id = str(uuid.uuid4())
    norm_data = {"financial_data": {}}
    result = FindingsBuilder.build_findings(doc_id, norm_data)
    assert result["status"] == "PARTIAL"
    assert result["findings"]["validations"][0]["status"] == "INCOMPLETE"
    assert result["findings"]["validations"][0]["is_valid"] is None


def test_findings_unit_yoy_growth_decline_unchanged():
    """Test 4: YoY variances with positive, negative, and unchanged directions."""
    doc_id = str(uuid.uuid4())
    norm_data = {
        "analysis": {
            "yoy": {
                "status": "COMPLETED",
                "financial_data": {
                    "revenue": {"current": 120.0, "previous": 100.0, "percentage_change": 20.0, "direction": "positive", "status": "COMPLETED"},
                    "net_profit": {"current": 80.0, "previous": 100.0, "percentage_change": -20.0, "direction": "negative", "status": "COMPLETED"},
                    "assets": {"current": 500.0, "previous": 500.0, "percentage_change": 0.0, "direction": "unchanged", "status": "COMPLETED"},
                }
            }
        }
    }
    result = FindingsBuilder.build_findings(doc_id, norm_data)
    variances = {v["field"]: v for v in result["findings"]["variances"]}
    assert variances["revenue"]["direction"] == "positive"
    assert variances["net_profit"]["direction"] == "negative"
    assert variances["assets"]["direction"] == "unchanged"


def test_findings_unit_yoy_insufficient_data():
    """Test 5: YoY insufficient data results in empty variances and warning."""
    doc_id = str(uuid.uuid4())
    norm_data = {
        "analysis": {
            "yoy": {
                "status": "INSUFFICIENT_DATA",
                "financial_data": {},
                "warnings": ["At least two periods required"],
                "reason": "Single period",
            }
        }
    }
    result = FindingsBuilder.build_findings(doc_id, norm_data)
    assert len(result["findings"]["variances"]) == 0
    assert "At least two periods required" in result["warnings"]


def test_findings_unit_ml_anomaly_detected():
    """Test 6: ML anomaly finding flags ANOMALY classification and is_anomaly True."""
    doc_id = str(uuid.uuid4())
    norm_data = {
        "ml_anomaly": {
            "is_anomaly": True,
            "score": -0.185,
            "prediction": -1,
            "label": "ANOMALY",
            "status": "COMPLETED",
            "model": {"type": "IsolationForest"},
            "warnings": ["Extreme ratio detected"],
            "reason": "Statistical outlier",
        }
    }
    result = FindingsBuilder.build_findings(doc_id, norm_data)
    anom = result["findings"]["anomalies"][0]
    assert anom["classification"] == "ANOMALY"
    assert anom["is_anomaly"] is True
    assert anom["anomaly_score"] == -0.185
    assert anom["prediction"] == -1
    assert "ml_anomaly: Extreme ratio detected" in result["warnings"]


def test_findings_unit_ml_missing():
    """Test 7: Missing ML anomaly detection produces warning and PARTIAL status."""
    doc_id = str(uuid.uuid4())
    norm_data = {}
    result = FindingsBuilder.build_findings(doc_id, norm_data)
    assert len(result["findings"]["anomalies"]) == 0
    assert any("ml_anomaly:" in w for w in result["warnings"])
    assert result["status"] == "PARTIAL"


def test_findings_unit_ratios_undefined_handling():
    """Test 8: Ratios with zero denominator are captured as UNDEFINED."""
    doc_id = str(uuid.uuid4())
    norm_data = {
        "analysis": {
            "ratios": {
                "status": "COMPLETED",
                "ratios": {
                    "liquidity": {
                        "current_ratio": {"value": None, "status": "UNDEFINED", "reason": "Current liabilities is zero"}
                    }
                },
                "warnings": ["Zero denominator in current_ratio"],
            }
        }
    }
    result = FindingsBuilder.build_findings(doc_id, norm_data)
    ratio = result["findings"]["ratios"][0]
    assert ratio["name"] == "current_ratio"
    assert ratio["status"] == "UNDEFINED"
    assert ratio["value"] is None
    assert ratio["reason"] == "Current liabilities is zero"


def test_findings_unit_evidence_traceability():
    """Test 9: Evidence correctly points to JSON path in normalized_data.financial_data."""
    doc_id = str(uuid.uuid4())
    norm_data = {
        "financial_data": {
            "revenue": 500000.0,
            "custom_metric": 12345.0,
        }
    }
    result = FindingsBuilder.build_findings(doc_id, norm_data)
    ev_map = {e["field"]: e for e in result["findings"]["evidence"]}
    
    assert ev_map["revenue"]["value"] == 500000.0
    assert ev_map["revenue"]["source"] == "normalized_data.financial_data.revenue"
    assert ev_map["revenue"]["is_available"] is True
    
    assert ev_map["assets"]["value"] is None
    assert ev_map["assets"]["is_available"] is False
    assert ev_map["assets"]["source"] == "normalized_data.financial_data.assets"
    
    assert ev_map["custom_metric"]["value"] == 12345.0
    assert ev_map["custom_metric"]["is_available"] is True


def test_findings_unit_nan_inf_sanitization():
    """Test 10: NaN and Inf values are cleanly converted to None for strict JSON serialization."""
    doc_id = str(uuid.uuid4())
    norm_data = {
        "financial_data": {
            "revenue": float("nan"),
            "assets": float("inf"),
        },
        "validation": {
            "balance_sheet_check": {
                "status": "INVALID",
                "difference": float("-inf"),
            }
        },
        "analysis": {
            "ratios": {
                "status": "COMPLETED",
                "ratios": {
                    "liquidity": {
                        "current_ratio": {"value": float("nan"), "status": "UNDEFINED"}
                    }
                }
            }
        }
    }
    result = FindingsBuilder.build_findings(doc_id, norm_data)
    ev_map = {e["field"]: e for e in result["findings"]["evidence"]}
    assert ev_map["revenue"]["value"] is None
    assert ev_map["assets"]["value"] is None
    assert result["findings"]["validations"][0]["difference"] is None
    assert result["findings"]["ratios"][0]["value"] is None


def test_findings_unit_warning_deduplication():
    """Test 11: Warnings from all sections are collected and deduplicated."""
    doc_id = str(uuid.uuid4())
    norm_data = {
        "analysis": {
            "yoy": {"status": "COMPLETED", "warnings": ["Duplicate warning", "YoY warning"]},
            "ratios": {"status": "COMPLETED", "warnings": ["Duplicate warning", "Ratio warning"]},
        }
    }
    result = FindingsBuilder.build_findings(doc_id, norm_data)
    assert result["warnings"].count("Duplicate warning") == 1
    assert "YoY warning" in result["warnings"]
    assert "Ratio warning" in result["warnings"]


# ==============================================================================
# 2. INTEGRATION TESTS — API & DATABASE PERSISTENCE
# ==============================================================================

def test_api_findings_invalid_uuid(client):
    """Test 12: Invalid UUID returns 400 Bad Request."""
    res = client.post("/api/v1/agent1/not-a-valid-uuid/findings")
    assert res.status_code == 400
    assert "Expected a valid UUID" in res.json()["detail"]


def test_api_findings_nonexistent_document(client):
    """Test 13: Nonexistent document returns 404 Not Found."""
    random_id = str(uuid.uuid4())
    res = client.post(f"/api/v1/agent1/{random_id}/findings")
    assert res.status_code == 404
    assert f"Document with ID '{random_id}' not found" in res.json()["detail"]


def test_api_findings_unnormalized_document(client, db_session):
    """Test 14: Document not in NORMALIZED status returns 400."""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="unnormalized.pdf",
        file_type="pdf",
        file_path="uploads/test.pdf",
        status=DocumentStatus.UPLOADED.value,
    )
    db_session.add(doc)
    db_session.commit()

    res = client.post(f"/api/v1/agent1/{doc_id}/findings")
    assert res.status_code == 400
    assert "has not been normalized yet" in res.json()["detail"]


def test_api_findings_e2e_success(client, db_session):
    """Test 15: Successful end-to-end findings generation and persistence for normalized document."""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="normalized_doc.pdf",
        file_type="pdf",
        file_path="uploads/normalized_doc.pdf",
        status=DocumentStatus.NORMALIZED.value,
    )
    db_session.add(doc)

    fin_data = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        company_name="Acme Corp",
        fiscal_year="2024",
        revenue=1000000.0,
        assets=2000000.0,
        liabilities=800000.0,
        equity=1200000.0,
        normalized_data={
            "financial_data": {
                "revenue": 1000000.0,
                "gross_profit": 400000.0,
                "net_profit": 150000.0,
                "assets": 2000000.0,
                "liabilities": 800000.0,
                "equity": 1200000.0,
                "current_assets": 600000.0,
                "current_liabilities": 300000.0,
                "inventory": 100000.0,
            },
            "previous_period_data": {
                "period": "2023",
                "financial_data": {
                    "revenue": 800000.0,
                    "gross_profit": 320000.0,
                    "net_profit": 120000.0,
                    "assets": 1600000.0,
                    "liabilities": 700000.0,
                    "equity": 900000.0,
                    "current_assets": 500000.0,
                    "current_liabilities": 250000.0,
                    "inventory": 80000.0,
                }
            }
        }
    )
    db_session.add(fin_data)
    db_session.commit()

    # Call findings endpoint directly without prior Agent 1 or ML calls
    res = client.post(f"/api/v1/agent1/{doc_id}/findings")
    assert res.status_code == 200
    data = res.json()
    assert data["document_id"] == doc_id
    assert data["status"] == "COMPLETED"
    
    findings = data["findings"]
    assert len(findings["validations"]) >= 1
    assert findings["validations"][0]["status"] == "VALID"
    assert len(findings["variances"]) > 0
    assert len(findings["anomalies"]) == 1
    assert findings["anomalies"][0]["classification"] in ("NORMAL", "ANOMALY")
    assert len(findings["ratios"]) > 0
    assert len(findings["evidence"]) >= 9

    # Verify DB persistence under normalized_data['analysis']['agent1_findings']
    db_session.expire_all()
    refreshed_rec = db_session.query(FinancialData).filter(FinancialData.document_id == doc_id).first()
    stored_norm = refreshed_rec.normalized_data
    assert "analysis" in stored_norm
    assert "agent1_findings" in stored_norm["analysis"]
    stored_findings = stored_norm["analysis"]["agent1_findings"]
    assert stored_findings["status"] == "COMPLETED"
    assert "validations" in stored_findings["findings"]


def test_api_findings_idempotency(client, db_session):
    """Test 16: Calling findings endpoint repeatedly updates in-place without side effects."""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="idempotent_doc.pdf",
        file_type="pdf",
        file_path="uploads/idempotent_doc.pdf",
        status=DocumentStatus.NORMALIZED.value,
    )
    db_session.add(doc)

    fin_data = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        company_name="Idempotent Corp",
        fiscal_year="2024",
        revenue=500000.0,
        assets=1000000.0,
        liabilities=400000.0,
        equity=600000.0,
        normalized_data={
            "financial_data": {
                "revenue": 500000.0,
                "assets": 1000000.0,
                "liabilities": 400000.0,
                "equity": 600000.0,
                "current_assets": 300000.0,
                "current_liabilities": 150000.0,
                "inventory": 50000.0,
                "gross_profit": 200000.0,
                "net_profit": 80000.0,
            }
        }
    )
    db_session.add(fin_data)
    db_session.commit()

    # Call twice
    res1 = client.post(f"/api/v1/agent1/{doc_id}/findings")
    assert res1.status_code == 200
    res2 = client.post(f"/api/v1/agent1/{doc_id}/findings")
    assert res2.status_code == 200

    # Ensure sibling data preserved
    db_session.expire_all()
    rec = db_session.query(FinancialData).filter(FinancialData.document_id == doc_id).first()
    assert "financial_data" in rec.normalized_data
    assert "agent1" in rec.normalized_data["analysis"]
    assert "agent1_findings" in rec.normalized_data["analysis"]
    assert "ml_anomaly" in rec.normalized_data


def test_api_findings_rollback_on_db_error(client, db_session, monkeypatch):
    """Test 17: Database failure triggers atomic rollback."""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="err_doc.pdf",
        file_type="pdf",
        file_path="uploads/err_doc.pdf",
        status=DocumentStatus.NORMALIZED.value,
    )
    db_session.add(doc)

    fin_data = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        company_name="Error Corp",
        fiscal_year="2024",
        revenue=100000.0,
        assets=200000.0,
        liabilities=50000.0,
        equity=150000.0,
        normalized_data={
            "financial_data": {
                "revenue": 100000.0,
                "assets": 200000.0,
                "liabilities": 50000.0,
                "equity": 150000.0,
            }
        }
    )
    db_session.add(fin_data)
    db_session.commit()

    from sqlalchemy.orm import Session
    def mock_commit(self):
        raise RuntimeError("Simulated DB commit error")

    monkeypatch.setattr(Session, "commit", mock_commit)

    res = client.post(f"/api/v1/agent1/{doc_id}/findings")
    assert res.status_code == 500
    assert "Failed to persist" in res.json()["detail"]


def test_findings_unit_incomplete_ratios():
    """Test 18: Incomplete ratios marked with INCOMPLETE and propagated reasons."""
    doc_id = str(uuid.uuid4())
    norm_data = {
        "analysis": {
            "ratios": {
                "status": "INCOMPLETE",
                "ratios": {
                    "liquidity": {
                        "current_ratio": {"value": None, "status": "INCOMPLETE", "reason": "Missing current_assets"}
                    }
                },
                "warnings": ["Missing required fields"],
                "reason": "Missing inputs",
            }
        }
    }
    result = FindingsBuilder.build_findings(doc_id, norm_data)
    assert result["status"] == "PARTIAL"
    assert result["findings"]["ratios"][0]["status"] == "INCOMPLETE"
    assert result["findings"]["ratios"][0]["reason"] == "Missing current_assets"


def test_findings_unit_yoy_zero_previous_value():
    """Test 19: YoY variance handles zero previous value with notice."""
    doc_id = str(uuid.uuid4())
    norm_data = {
        "analysis": {
            "yoy": {
                "status": "COMPLETED",
                "financial_data": {
                    "revenue": {
                        "current": 500.0,
                        "previous": 0.0,
                        "absolute_change": 500.0,
                        "percentage_change": None,
                        "direction": "positive",
                        "status": "INCOMPLETE",
                        "reason": "Previous period value is zero; percentage change undefined",
                    }
                }
            }
        }
    }
    result = FindingsBuilder.build_findings(doc_id, norm_data)
    var = result["findings"]["variances"][0]
    assert var["percentage_change"] is None
    assert var["status"] == "INCOMPLETE"
    assert "undefined" in var["reason"]


def test_findings_unit_zero_difference_balance_sheet():
    """Test 20: Balance sheet difference of exactly 0.0 is strictly valid."""
    doc_id = str(uuid.uuid4())
    norm_data = {
        "validation": {
            "balance_sheet_check": {
                "status": "VALID",
                "is_valid": True,
                "difference": 0.0,
                "tolerance": 0.01,
            }
        }
    }
    result = FindingsBuilder.build_findings(doc_id, norm_data)
    v = result["findings"]["validations"][0]
    assert v["status"] == "VALID"
    assert v["is_valid"] is True
    assert v["difference"] == 0.0


def test_findings_unit_within_tolerance_balance_sheet():
    """Test 21: Balance sheet difference within tolerance is VALID."""
    doc_id = str(uuid.uuid4())
    norm_data = {
        "validation": {
            "balance_sheet_check": {
                "status": "VALID",
                "is_valid": True,
                "difference": 0.005,
                "tolerance": 0.01,
            }
        }
    }
    result = FindingsBuilder.build_findings(doc_id, norm_data)
    v = result["findings"]["validations"][0]
    assert v["status"] == "VALID"
    assert v["is_valid"] is True
    assert v["difference"] == 0.005


def test_findings_unit_ml_score_boundary():
    """Test 22: ML score boundary conditions (negative anomaly, non-negative normal)."""
    doc_id = str(uuid.uuid4())
    norm_data = {
        "ml_anomaly": {
            "is_anomaly": False,
            "score": 0.125,
            "prediction": 1,
            "label": "NORMAL",
            "status": "COMPLETED",
        }
    }
    result = FindingsBuilder.build_findings(doc_id, norm_data)
    anom = result["findings"]["anomalies"][0]
    assert anom["anomaly_score"] == 0.125
    assert anom["classification"] == "NORMAL"


def test_findings_unit_evidence_all_none():
    """Test 23: When all financial fields are missing, evidence shows is_available False."""
    doc_id = str(uuid.uuid4())
    norm_data = {"financial_data": {}}
    result = FindingsBuilder.build_findings(doc_id, norm_data)
    for ev in result["findings"]["evidence"]:
        assert ev["value"] is None
        assert ev["is_available"] is False


def test_findings_unit_fallback_to_agent1_results():
    """Test 24: FindingsBuilder retrieves validation/yoy/ratios from analysis.agent1 if top-level missing."""
    doc_id = str(uuid.uuid4())
    norm_data = {
        "analysis": {
            "agent1": {
                "results": {
                    "math_validation": {"status": "VALID", "is_valid": True, "difference": 0.0},
                    "yoy_analysis": {
                        "status": "COMPLETED",
                        "periods": {"current_period": "2024", "previous_period": "2023"},
                        "financial_data": {
                            "revenue": {"current": 100.0, "previous": 80.0, "percentage_change": 25.0, "status": "COMPLETED"}
                        }
                    },
                    "financial_ratios": {
                        "status": "COMPLETED",
                        "ratios": {
                            "liquidity": {
                                "current_ratio": {"value": 1.5, "status": "COMPLETED"}
                            }
                        }
                    }
                }
            }
        },
        "ml_anomaly": {"is_anomaly": False, "score": 0.05, "prediction": 1, "label": "NORMAL", "status": "COMPLETED"},
        "financial_data": {"revenue": 100.0}
    }
    result = FindingsBuilder.build_findings(doc_id, norm_data)
    assert result["status"] == "COMPLETED"
    assert result["findings"]["validations"][0]["status"] == "VALID"
    assert len(result["findings"]["variances"]) == 1
    assert len(result["findings"]["ratios"]) == 1


def test_findings_unit_pydantic_container_serialization():
    """Test 25: Ensure FindingsContainer and Agent1FindingsResponse serialize to dict / JSON cleanly."""
    doc_id = str(uuid.uuid4())
    raw = FindingsBuilder.build_findings(doc_id, {"financial_data": {"revenue": 100.0}})
    response_model = Agent1FindingsResponse(**raw)
    dumped = response_model.model_dump()
    assert dumped["document_id"] == doc_id
    assert "findings" in dumped
    assert "evidence" in dumped["findings"]


def test_findings_unit_whitespace_in_warnings():
    """Test 26: Empty and whitespace warnings are ignored during warning deduplication."""
    doc_id = str(uuid.uuid4())
    norm_data = {
        "analysis": {
            "yoy": {"warnings": ["", "   ", "Valid warning"]},
        }
    }
    result = FindingsBuilder.build_findings(doc_id, norm_data)
    assert "" not in result["warnings"]
    assert "   " not in result["warnings"]
    assert "Valid warning" in result["warnings"]


def test_findings_unit_custom_evidence_fields():
    """Test 27: Custom extra fields in financial_data are retained in evidence."""
    doc_id = str(uuid.uuid4())
    norm_data = {
        "financial_data": {
            "ebitda": 250000.0,
            "operating_cash_flow": 180000.0,
        }
    }
    result = FindingsBuilder.build_findings(doc_id, norm_data)
    fields = [e["field"] for e in result["findings"]["evidence"]]
    assert "ebitda" in fields
    assert "operating_cash_flow" in fields


def test_api_findings_auto_generate_agent1_and_ml(client, db_session):
    """Test 28: Direct invocation of /findings auto-generates Agent 1 and ML Anomaly sections."""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="auto_doc.pdf",
        file_type="pdf",
        file_path="uploads/auto_doc.pdf",
        status=DocumentStatus.NORMALIZED.value,
    )
    db_session.add(doc)

    fin_data = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        company_name="Auto Corp",
        fiscal_year="2024",
        revenue=300000.0,
        assets=600000.0,
        liabilities=200000.0,
        equity=400000.0,
        normalized_data={
            "financial_data": {
                "revenue": 300000.0,
                "assets": 600000.0,
                "liabilities": 200000.0,
                "equity": 400000.0,
                "current_assets": 200000.0,
                "current_liabilities": 100000.0,
                "inventory": 40000.0,
                "gross_profit": 120000.0,
                "net_profit": 50000.0,
            }
        }
    )
    db_session.add(fin_data)
    db_session.commit()

    res = client.post(f"/api/v1/agent1/{doc_id}/findings")
    assert res.status_code == 200
    data = res.json()
    assert data["document_id"] == doc_id
    # Validations, ML anomaly, and Ratios should all be populated
    assert len(data["findings"]["validations"]) >= 1
    assert len(data["findings"]["anomalies"]) >= 1
    assert len(data["findings"]["ratios"]) >= 1


def test_findings_unit_extreme_ratio_values():
    """Test 29: Extreme but finite ratio values serialize properly without overflow."""
    doc_id = str(uuid.uuid4())
    norm_data = {
        "analysis": {
            "ratios": {
                "status": "COMPLETED",
                "ratios": {
                    "leverage": {
                        "debt_to_equity": {"value": 999999999.99, "status": "COMPLETED"}
                    }
                }
            }
        }
    }
    result = FindingsBuilder.build_findings(doc_id, norm_data)
    assert result["findings"]["ratios"][0]["value"] == 999999999.99


def test_findings_unit_ml_reason_propagation():
    """Test 30: ML anomaly explanation/reason is preserved in findings."""
    doc_id = str(uuid.uuid4())
    norm_data = {
        "ml_anomaly": {
            "is_anomaly": True,
            "score": -0.22,
            "prediction": -1,
            "label": "ANOMALY",
            "reason": "Extreme debt-to-equity ratio observed",
        }
    }
    result = FindingsBuilder.build_findings(doc_id, norm_data)
    assert result["findings"]["anomalies"][0]["reason"] == "Extreme debt-to-equity ratio observed"


def test_findings_unit_yoy_negative_delta():
    """Test 31: YoY percentage change with negative value preserves correct sign."""
    doc_id = str(uuid.uuid4())
    norm_data = {
        "analysis": {
            "yoy": {
                "status": "COMPLETED",
                "financial_data": {
                    "net_profit": {
                        "current": -50.0,
                        "previous": 100.0,
                        "absolute_change": -150.0,
                        "percentage_change": -150.0,
                        "direction": "negative",
                        "status": "COMPLETED",
                    }
                }
            }
        }
    }
    result = FindingsBuilder.build_findings(doc_id, norm_data)
    v = result["findings"]["variances"][0]
    assert v["percentage_change"] == -150.0
    assert v["absolute_change"] == -150.0
    assert v["direction"] == "negative"


def test_findings_unit_deterministic_repeatability():
    """Test 32: Multiple invocations of build_findings with identical input return identical output."""
    doc_id = str(uuid.uuid4())
    norm_data = {
        "financial_data": {"revenue": 100.0, "assets": 200.0},
        "validation": {"balance_sheet_check": {"status": "VALID", "is_valid": True, "difference": 0.0}},
    }
    out1 = FindingsBuilder.build_findings(doc_id, norm_data)
    out2 = FindingsBuilder.build_findings(doc_id, norm_data)
    assert out1 == out2
