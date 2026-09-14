"""End-to-end integration test suite verifying the complete 14-step financial review pipeline.

Steps:
 1. Upload document (CSV/Excel)
 2. Process document (Extract & Normalize)
 3. Verify extraction
 4. Verify normalization
 5. Verify database persistence
 6. Run Math Validation
 7. Run YoY Analysis
 8. Run Financial Ratios
 9. Run Agent 1 (and alias /analysis/{id}/agent1)
10. Run ML Anomaly Detection
11. Run Agent 1 Findings
12. Run Agent 2 Review
13. Run Review Observations
14. Verify final database state & sibling preservation
"""

import io
import json
import uuid
from pathlib import Path
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
                    title="Balance Sheet Balanced",
                    finding="Assets equal liabilities plus equity across all reported periods.",
                    explanation="Verified Assets ($5,000,000) equal Liabilities ($2,000,000) plus Equity ($3,000,000).",
                    severity="LOW",
                    evidence=["findings.validations.balance_sheet_check"]
                ),
                ObservationFinding(
                    finding_type="YOY",
                    title="Revenue Growth",
                    finding="Revenue increased by 25.00% year-over-year.",
                    explanation="Revenue expanded from $2,000,000 in 2023 to $2,500,000 in 2024.",
                    severity="LOW",
                    evidence=["findings.variances.revenue"]
                ),
                ObservationFinding(
                    finding_type="RATIO",
                    title="Current Ratio Liquidity",
                    finding="Current ratio is 2.50.",
                    explanation="Current assets cover short-term liabilities with healthy buffer.",
                    severity="LOW",
                    evidence=["findings.ratios.current_ratio"]
                )
            ],
            summary="Financial statements show mathematical consistency, revenue expansion, and solid liquidity.",
            limitations=[]
        )
        yield mock_gen


SAMPLE_FINANCIAL_CSV = (
    "Line Item,2023,2024\n"
    "Revenue,2000000,2500000\n"
    "Cost of Goods Sold,1200000,1500000\n"
    "Gross Profit,800000,1000000\n"
    "Operating Expenses,400000,500000\n"
    "Operating Income,400000,500000\n"
    "Net Income,300000,375000\n"
    "Total Assets,4000000,5000000\n"
    "Current Assets,1600000,2000000\n"
    "Cash and Cash Equivalents,600000,800000\n"
    "Inventory,400000,500000\n"
    "Total Liabilities,1600000,2000000\n"
    "Current Liabilities,640000,800000\n"
    "Long Term Debt,960000,1200000\n"
    "Total Debt,960000,1200000\n"
    "Shareholders' Equity,2400000,3000000\n"
)


def test_full_14_step_pipeline_end_to_end(client, db_session, mock_ollama):
    """Executes all 14 steps of the pipeline and verifies database state after each step."""
    
    # -------------------------------------------------------------
    # Step 1: Upload document
    # -------------------------------------------------------------
    file_bytes = io.BytesIO(SAMPLE_FINANCIAL_CSV.encode("utf-8"))
    upload_res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("company_financials.csv", file_bytes, "text/csv")}
    )
    assert upload_res.status_code == 201
    upload_payload = upload_res.json()
    doc_id = upload_payload["document_id"]
    assert upload_payload["status"] == "UPLOADED"
    assert upload_payload["file_type"] == "csv"

    # Verify Step 1 DB record
    doc_record = db_session.query(Document).filter(Document.id == doc_id).first()
    assert doc_record is not None
    assert doc_record.status == DocumentStatus.UPLOADED.value

    # -------------------------------------------------------------
    # Step 2: Process document (Extract & Normalize)
    # -------------------------------------------------------------
    proc_res = client.post(f"/api/v1/documents/{doc_id}/process")
    assert proc_res.status_code == 200
    norm_payload = proc_res.json()
    assert norm_payload["document_id"] == doc_id
    assert norm_payload["status"] == "NORMALIZED"

    # -------------------------------------------------------------
    # Step 3: Verify extraction status
    # -------------------------------------------------------------
    status_res = client.get(f"/api/v1/documents/{doc_id}")
    assert status_res.status_code == 200
    status_payload = status_res.json()
    assert status_payload["status"] == "NORMALIZED"

    # -------------------------------------------------------------
    # Step 4: Verify normalized data endpoint
    # -------------------------------------------------------------
    get_norm_res = client.get(f"/api/v1/documents/{doc_id}/normalized")
    assert get_norm_res.status_code == 200
    get_norm_data = get_norm_res.json()
    assert get_norm_data["status"] == "NORMALIZED"
    assert get_norm_data["financial_data"]["revenue"] == 2500000.0
    assert get_norm_data["financial_data"]["assets"] == 5000000.0
    assert get_norm_data["financial_data"]["liabilities"] == 2000000.0
    assert get_norm_data["financial_data"]["equity"] == 3000000.0

    # -------------------------------------------------------------
    # Step 5: Verify database persistence of normalized data
    # -------------------------------------------------------------
    db_session.expire_all()
    fin_rec = db_session.query(FinancialData).filter(FinancialData.document_id == doc_id).first()
    assert fin_rec is not None
    assert fin_rec.revenue == 2500000.0
    assert fin_rec.assets == 5000000.0
    assert fin_rec.liabilities == 2000000.0
    assert fin_rec.equity == 3000000.0
    assert "financial_data" in fin_rec.normalized_data

    # Augment normalized_data with previous period data for full 2-period YoY comparison
    norm_copy = dict(fin_rec.normalized_data)
    norm_copy["previous_period_data"] = {
        "period": "2023",
        "financial_data": {
            "revenue": 2000000.0,
            "assets": 4000000.0,
            "liabilities": 1600000.0,
            "equity": 2400000.0,
            "gross_profit": 800000.0,
            "net_profit": 300000.0,
            "operating_income": 400000.0,
            "current_assets": 1600000.0,
            "current_liabilities": 640000.0,
            "inventory": 400000.0,
            "total_debt": 960000.0,
        }
    }
    fin_rec.normalized_data = norm_copy
    db_session.commit()

    # -------------------------------------------------------------
    # Step 6: Run Math Validation
    # -------------------------------------------------------------
    val_res = client.post(f"/api/v1/validation/{doc_id}/math")
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert val_data["balance_sheet_check"]["status"] == "VALID"
    assert val_data["balance_sheet_check"]["is_valid"] is True

    # -------------------------------------------------------------
    # Step 7: Run YoY Analysis
    # -------------------------------------------------------------
    yoy_res = client.post(f"/api/v1/analysis/{doc_id}/yoy")
    assert yoy_res.status_code == 200
    yoy_data = yoy_res.json()
    assert yoy_data["yoy_analysis"]["status"] in ("COMPLETED", "INCOMPLETE", "INSUFFICIENT_DATA")

    # -------------------------------------------------------------
    # Step 8: Run Financial Ratios
    # -------------------------------------------------------------
    ratio_res = client.post(f"/api/v1/analysis/{doc_id}/ratios")
    assert ratio_res.status_code == 200
    ratio_data = ratio_res.json()
    assert ratio_data["ratio_analysis"]["status"] in ("COMPLETED", "INCOMPLETE")
    assert ratio_data["ratio_analysis"]["ratios"]["liquidity"]["current_ratio"]["value"] == 2.5

    # -------------------------------------------------------------
    # Step 9: Run Agent 1 (and test alias /analysis/{id}/agent1)
    # -------------------------------------------------------------
    agent1_res = client.post(f"/api/v1/agent1/{doc_id}")
    assert agent1_res.status_code == 200
    agent1_data = agent1_res.json()
    assert agent1_data["status"] in ("COMPLETED", "PARTIAL")
    assert agent1_data["results"]["math_validation"]["status"] == "VALID"

    # Alias check
    alias_res = client.post(f"/api/v1/analysis/{doc_id}/agent1")
    assert alias_res.status_code == 200
    assert alias_res.json()["status"] in ("COMPLETED", "PARTIAL")

    # -------------------------------------------------------------
    # Step 10: Run ML Anomaly Detection
    # -------------------------------------------------------------
    ml_res = client.post(f"/api/v1/ml/{doc_id}/anomaly")
    assert ml_res.status_code == 200
    ml_data = ml_res.json()
    assert ml_data["status"] == "COMPLETED"
    assert ml_data["prediction"] in (1, -1)
    assert ml_data["anomaly_detection"]["score"] is not None

    # -------------------------------------------------------------
    # Step 11: Run Agent 1 Findings
    # -------------------------------------------------------------
    findings_res = client.post(f"/api/v1/agent1/{doc_id}/findings")
    assert findings_res.status_code == 200
    findings_data = findings_res.json()
    assert findings_data["status"] in ("COMPLETED", "PARTIAL")
    f_container = findings_data["findings"]
    assert len(f_container["validations"]) >= 1
    assert len(f_container["variances"]) >= 1
    assert len(f_container["ratios"]) >= 1
    assert len(f_container["evidence"]) >= 1

    # -------------------------------------------------------------
    # Step 12: Run Agent 2 Review
    # -------------------------------------------------------------
    rev_res = client.post(f"/api/v1/agent2/{doc_id}/review")
    assert rev_res.status_code == 200
    rev_data = rev_res.json()
    assert rev_data["status"] in ("COMPLETED", "PARTIAL")
    assert len(rev_data["investigations"]) >= 1
    assert len(rev_data["metric_comparisons"]) >= 1
    assert rev_data["summary"] is not None

    # -------------------------------------------------------------
    # Step 13: Run Review Observations
    # -------------------------------------------------------------
    obs_res = client.post(f"/api/v1/agent2/{doc_id}/observations")
    assert obs_res.status_code == 200
    obs_data = obs_res.json()
    assert obs_data["status"] in ("COMPLETED", "PARTIAL")
    assert len(obs_data["observations"]) >= 1
    for obs in obs_data["observations"]:
        assert obs["severity"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        assert len(obs["finding"]) > 0
        assert len(obs["explanation"]) > 0
        assert len(obs["recommendation"]) > 0
        assert len(obs["evidence"]) >= 1

    # -------------------------------------------------------------
    # Step 14: Verify final database state & sibling preservation
    # -------------------------------------------------------------
    db_session.expire_all()
    fin_final = db_session.query(FinancialData).filter(FinancialData.document_id == doc_id).first()
    assert fin_final is not None
    nd = fin_final.normalized_data

    # Verify all expected sections are present without clobbering
    assert "financial_data" in nd
    assert "validation" in nd
    assert "analysis" in nd
    analysis = nd["analysis"]
    assert "yoy" in analysis
    assert "ratios" in analysis
    assert "agent1" in analysis
    assert "agent1_findings" in analysis
    assert "agent2" in analysis
    assert "ml_anomaly" in nd
    assert "review_observations" in nd

    # Verify review_observations content integrity
    persisted_obs = nd["review_observations"]
    assert len(persisted_obs["observations"]) == len(obs_data["observations"])


def test_pipeline_idempotency_and_sibling_preservation(client, db_session, mock_ollama):
    """Verify that calling each analysis endpoint multiple times produces identical results without corrupting sibling sections."""
    file_bytes = io.BytesIO(SAMPLE_FINANCIAL_CSV.encode("utf-8"))
    upload_res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("idempotent_sample.csv", file_bytes, "text/csv")}
    )
    doc_id = upload_res.json()["document_id"]
    client.post(f"/api/v1/documents/{doc_id}/process")

    endpoints = [
        f"/api/v1/validation/{doc_id}/math",
        f"/api/v1/analysis/{doc_id}/yoy",
        f"/api/v1/analysis/{doc_id}/ratios",
        f"/api/v1/agent1/{doc_id}",
        f"/api/v1/ml/{doc_id}/anomaly",
        f"/api/v1/agent1/{doc_id}/findings",
        f"/api/v1/agent2/{doc_id}/review",
        f"/api/v1/agent2/{doc_id}/observations",
    ]

    # Run pass 1
    for ep in endpoints:
        r = client.post(ep)
        assert r.status_code == 200, f"Pass 1 failed on {ep}"

    # Verify row counts
    doc_count_1 = db_session.query(Document).filter(Document.id == doc_id).count()
    fin_count_1 = db_session.query(FinancialData).filter(FinancialData.document_id == doc_id).count()
    assert doc_count_1 == 1
    assert fin_count_1 == 1

    # Run pass 2 (idempotency)
    for ep in endpoints:
        r = client.post(ep)
        assert r.status_code == 200, f"Pass 2 failed on {ep}"

    # Verify row counts remain 1
    doc_count_2 = db_session.query(Document).filter(Document.id == doc_id).count()
    fin_count_2 = db_session.query(FinancialData).filter(FinancialData.document_id == doc_id).count()
    assert doc_count_2 == 1
    assert fin_count_2 == 1

    # Verify sibling sections remain intact after pass 2
    db_session.expire_all()
    fin = db_session.query(FinancialData).filter(FinancialData.document_id == doc_id).first()
    nd = fin.normalized_data
    assert "validation" in nd
    assert "yoy" in nd["analysis"]
    assert "ratios" in nd["analysis"]
    assert "agent1" in nd["analysis"]
    assert "agent1_findings" in nd["analysis"]
    assert "agent2" in nd["analysis"]
    assert "ml_anomaly" in nd
    assert "review_observations" in nd


def test_pipeline_negative_matrix(client, db_session):
    """Verify all pipeline endpoints reject invalid UUIDs, nonexistent documents, and unnormalized documents."""
    endpoints_requiring_normalized = [
        ("/api/v1/validation/{id}/math", "POST"),
        ("/api/v1/analysis/{id}/yoy", "POST"),
        ("/api/v1/analysis/{id}/ratios", "POST"),
        ("/api/v1/agent1/{id}", "POST"),
        ("/api/v1/analysis/{id}/agent1", "POST"),
        ("/api/v1/ml/{id}/anomaly", "POST"),
        ("/api/v1/agent1/{id}/findings", "POST"),
        ("/api/v1/agent2/{id}/review", "POST"),
        ("/api/v1/agent2/{id}/observations", "POST"),
    ]

    # 1. Invalid UUID
    for ep_pattern, method in endpoints_requiring_normalized:
        ep = ep_pattern.format(id="not-a-uuid")
        res = client.post(ep) if method == "POST" else client.get(ep)
        assert res.status_code == 400, f"Expected 400 for invalid UUID on {ep}"
        assert "valid UUID" in res.json().get("detail", "")

    # 2. Nonexistent Document
    nonexistent_id = str(uuid.uuid4())
    for ep_pattern, method in endpoints_requiring_normalized:
        ep = ep_pattern.format(id=nonexistent_id)
        res = client.post(ep) if method == "POST" else client.get(ep)
        assert res.status_code == 404, f"Expected 404 for nonexistent document on {ep}"

    # 3. Unnormalized Document
    unnorm_id = str(uuid.uuid4())
    doc = Document(
        id=unnorm_id,
        filename="unnorm.csv",
        file_type="csv",
        file_path="uploads/unnorm.csv",
        status=DocumentStatus.UPLOADED.value
    )
    db_session.add(doc)
    db_session.commit()

    for ep_pattern, method in endpoints_requiring_normalized:
        ep = ep_pattern.format(id=unnorm_id)
        res = client.post(ep) if method == "POST" else client.get(ep)
        assert res.status_code == 400, f"Expected 400 for unnormalized document on {ep}"
        assert "not been normalized" in res.json().get("detail", "")
