"""Standalone verification script for Step 4.1 — Agent 2: AI Financial Review Agent."""

import json
import uuid
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.database.database import SessionLocal
from app.models.document import Document, DocumentStatus
from app.models.financial_data import FinancialData
from app.services.agent2.investigation import InvestigationService
from app.services.agent2.metric_comparator import MetricComparator
from app.schemas.agent2 import OllamaReviewContent, ObservationFinding


def run_verification():
    print("==================================================")
    print("STEP 4.1 — AGENT 2 VERIFICATION")
    print("==================================================")

    client = TestClient(app)
    db = SessionLocal()

    try:
        # Check 1: Investigation Service
        test_findings = {
            "validations": [{
                "type": "BALANCE_SHEET_VALIDATION",
                "status": "VALID",
                "difference": 0.0,
                "tolerance": 0.01,
            }],
            "variances": [{
                "field": "revenue",
                "current_period": "2024",
                "previous_period": "2023",
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
                "model_type": "IsolationForest",
            }],
            "ratios": [{
                "name": "current_ratio",
                "category": "liquidity",
                "status": "COMPLETED",
                "value": 2.0,
            }],
            "evidence": [
                {"field": "revenue", "value": 1200000.0, "is_available": True},
                {"field": "net_profit", "value": 200000.0, "is_available": True},
            ]
        }

        investigations = InvestigationService.investigate(test_findings)
        assert len(investigations) >= 4
        print("  [OK] Check 1: InvestigationService PASSED")

        # Check 2: Metric Comparator
        comparisons = MetricComparator.compare_metrics(test_findings)
        assert len(comparisons) >= 1
        assert comparisons[0]["metric_a"] == "revenue"
        assert comparisons[0]["metric_b"] == "net_profit"
        assert comparisons[0]["relationship"] == "both_positive_profitable"
        print("  [OK] Check 2: MetricComparator PASSED")

        # Check 3: API execution with mock Ollama
        mock_content = OllamaReviewContent(
            observations=[
                ObservationFinding(
                    finding_type="VALIDATION",
                    title="Balance Sheet Equality",
                    finding="Assets equal liabilities plus equity.",
                    explanation="Verified balance holds strictly within tolerance.",
                    severity="LOW",
                    evidence=["findings.validations.balance_sheet_check"]
                ),
                ObservationFinding(
                    finding_type="YOY",
                    title="Revenue Expansion",
                    finding="Revenue grew by 20.00%.",
                    explanation="Reported top-line increased from 1,000,000 to 1,200,000.",
                    severity="LOW",
                    evidence=["findings.variances.revenue"]
                )
            ],
            summary="Strong liquidity and balanced sheet observed.",
            limitations=[]
        )

        doc_id = str(uuid.uuid4())
        doc = Document(
            id=doc_id,
            filename="verify_agent2.pdf",
            file_type="pdf",
            file_path="uploads/verify_agent2.pdf",
            status=DocumentStatus.NORMALIZED.value,
        )
        db.add(doc)

        fin_data = FinancialData(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            company_name="Agent2 Verify Co",
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

        with patch("app.services.agent2.ollama_client.OllamaClient.generate_review", return_value=mock_content):
            resp = client.post(f"/api/v1/agent2/{doc_id}/review")
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            payload = resp.json()
            assert payload["document_id"] == doc_id
            assert payload["status"] in ("COMPLETED", "PARTIAL")
            assert len(payload["investigations"]) > 0
            assert len(payload["metric_comparisons"]) > 0
            assert len(payload["observations"]) == 2
            print("  [OK] Check 3: API POST /api/v1/agent2/{id}/review PASSED")

        # Check 4: Database persistence verification
        db.expire_all()
        refreshed = db.query(FinancialData).filter(FinancialData.document_id == doc_id).first()
        norm = refreshed.normalized_data
        assert "analysis" in norm
        assert "agent2" in norm["analysis"]
        assert "agent1_findings" in norm["analysis"]
        assert norm["analysis"]["agent2"]["status"] in ("COMPLETED", "PARTIAL")
        print("  [OK] Check 4: Database persistence under analysis.agent2 PASSED")

        # Check 5: Idempotency
        with patch("app.services.agent2.ollama_client.OllamaClient.generate_review", return_value=mock_content):
            resp2 = client.post(f"/api/v1/agent2/{doc_id}/review")
            assert resp2.status_code == 200
        print("  [OK] Check 5: Idempotency PASSED")

        print("==================================================")
        print("ALL VERIFICATION CHECKS PASSED: FINAL STATUS: PASS")
        print("==================================================")

    finally:
        db.close()


if __name__ == "__main__":
    run_verification()
