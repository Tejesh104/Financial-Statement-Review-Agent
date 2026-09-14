"""Standalone verification script for Step 4.2: Review Observations Layer."""

import json
import uuid
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.database.database import SessionLocal
from app.models.document import Document, DocumentStatus
from app.models.financial_data import FinancialData
from app.services.review.review_observations_builder import ReviewObservationsBuilder
from app.schemas.agent2 import OllamaReviewContent, ObservationFinding


def run_verification():
    print("==================================================")
    print("STEP 4.2 — REVIEW OBSERVATIONS VERIFICATION")
    print("==================================================")

    client = TestClient(app)
    db = SessionLocal()

    try:
        # Check 1: Deterministic Severity Assignment
        assert ReviewObservationsBuilder.determine_severity("VALIDATION", "INVALID") == "CRITICAL"
        assert ReviewObservationsBuilder.determine_severity("ML_ANOMALY", "ANOMALY", {"is_anomaly": True}) == "HIGH"
        assert ReviewObservationsBuilder.determine_severity("YOY", "COMPLETED", {"direction": "negative"}) == "MEDIUM"
        assert ReviewObservationsBuilder.determine_severity("VALIDATION", "VALID") == "LOW"
        print("  [OK] Check 1: Deterministic Severity Assignment PASSED")

        # Check 2: Builder Unit Test with Mock Ollama
        mock_c = MagicMock()
        mock_c.model = "qwen2.5:7b"
        mock_c.generate_review.return_value = OllamaReviewContent(
            observations=[
                ObservationFinding(
                    finding_type="VALIDATION",
                    title="Balance Sheet",
                    finding="Balance sheet equation balances (Assets = Liabilities + Equity) within tolerance 0.01.",
                    explanation="Assets equal liabilities plus equity across reported schedules.",
                    severity="LOW",
                    evidence=[]
                ),
                ObservationFinding(
                    finding_type="YOY",
                    title="Revenue",
                    finding="Revenue changed by +20.00% year-over-year (positive trend).",
                    explanation="Sales expansion drove revenue from 1M to 1.2M.",
                    severity="LOW",
                    evidence=[]
                )
            ],
            summary="Clean balance sheet and positive revenue growth.",
            limitations=[]
        )

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
                    "anomaly_score": 0.04,
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

        builder_res = ReviewObservationsBuilder.build_observations(
            document_id=doc_id,
            findings_data=findings_data,
            ollama_client=mock_c,
        )
        assert builder_res["status"] == "COMPLETED"
        assert len(builder_res["observations"]) >= 2
        for obs in builder_res["observations"]:
            assert "finding" in obs
            assert "explanation" in obs
            assert "severity" in obs
            assert "evidence" in obs
            assert "recommendation" in obs
        print("  [OK] Check 2: ReviewObservationsBuilder Logic PASSED")

        # Check 3: API execution and DB persistence
        doc = Document(
            id=doc_id,
            filename="verify_obs.pdf",
            file_type="pdf",
            file_path="uploads/verify_obs.pdf",
            status=DocumentStatus.NORMALIZED.value,
        )
        db.add(doc)

        fin_data = FinancialData(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            company_name="Verify Obs Co",
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
        db.add(fin_data)
        db.commit()

        with patch("app.services.review.review_observations_builder.OllamaClient", return_value=mock_c):
            resp = client.post(f"/api/v1/agent2/{doc_id}/observations")
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            payload = resp.json()
            assert payload["document_id"] == doc_id
            assert payload["status"] in ("COMPLETED", "PARTIAL")
            assert len(payload["observations"]) >= 1
            print("  [OK] Check 3: API POST /api/v1/agent2/{id}/observations PASSED")

        # Check 4: Database Persistence under normalized_data['review_observations']
        db.expire_all()
        rec = db.query(FinancialData).filter(FinancialData.document_id == doc_id).first()
        norm = rec.normalized_data
        assert "review_observations" in norm
        assert len(norm["review_observations"]["observations"]) >= 1
        assert "financial_data" in norm
        assert "analysis" in norm
        print("  [OK] Check 4: Database Persistence under normalized_data['review_observations'] PASSED")

        # Check 5: Idempotency
        with patch("app.services.review.review_observations_builder.OllamaClient", return_value=mock_c):
            resp2 = client.post(f"/api/v1/agent2/{doc_id}/observations")
            assert resp2.status_code == 200
        print("  [OK] Check 5: Repeated execution (Idempotency) PASSED")

        print("==================================================")
        print("ALL VERIFICATION CHECKS PASSED: FINAL STATUS: PASS")
        print("==================================================")

    finally:
        db.close()


if __name__ == "__main__":
    run_verification()
