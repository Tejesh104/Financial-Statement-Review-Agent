"""Comprehensive verification script for Step 3.6 — Agent 1 Findings Layer."""

import json
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.database.database import SessionLocal
from app.models.document import Document, DocumentStatus
from app.models.financial_data import FinancialData
from app.services.agent1.findings_builder import FindingsBuilder

def run_verification():
    print("==================================================")
    print("STEP 3.6 — AGENT 1 FINDINGS VERIFICATION")
    print("==================================================")

    client = TestClient(app)
    db = SessionLocal()

    try:
        # Case 1: Pure unit extraction & structure check
        doc_id = str(uuid.uuid4())
        norm_data = {
            "financial_data": {
                "revenue": 1200000.0,
                "gross_profit": 500000.0,
                "net_profit": 180000.0,
                "assets": 2500000.0,
                "liabilities": 1000000.0,
                "equity": 1500000.0,
                "current_assets": 800000.0,
                "current_liabilities": 400000.0,
                "inventory": 150000.0,
            },
            "validation": {
                "balance_sheet_check": {
                    "status": "VALID",
                    "is_valid": True,
                    "difference": 0.0,
                    "tolerance": 0.01,
                }
            },
            "analysis": {
                "yoy": {
                    "status": "COMPLETED",
                    "periods": {"current_period": "2024", "previous_period": "2023"},
                    "financial_data": {
                        "revenue": {
                            "current": 1200000.0,
                            "previous": 1000000.0,
                            "absolute_change": 200000.0,
                            "percentage_change": 20.0,
                            "direction": "positive",
                            "status": "COMPLETED",
                        }
                    },
                    "warnings": [],
                },
                "ratios": {
                    "status": "COMPLETED",
                    "ratios": {
                        "liquidity": {
                            "current_ratio": {"value": 2.0, "status": "COMPLETED"}
                        }
                    },
                    "warnings": [],
                }
            },
            "ml_anomaly": {
                "is_anomaly": False,
                "score": -0.045,
                "prediction": 1,
                "label": "NORMAL",
                "status": "COMPLETED",
                "model": {"type": "IsolationForest"},
                "warnings": [],
            }
        }

        findings_res = FindingsBuilder.build_findings(doc_id, norm_data)
        assert findings_res["status"] == "COMPLETED"
        assert len(findings_res["findings"]["validations"]) == 1
        assert len(findings_res["findings"]["variances"]) == 1
        assert len(findings_res["findings"]["anomalies"]) == 1
        assert len(findings_res["findings"]["ratios"]) == 1
        assert len(findings_res["findings"]["evidence"]) >= 9
        print("  [OK] Case 1: FindingsBuilder structure & extraction PASSED")

        # Case 2: Full API execution & DB persistence
        api_doc_id = str(uuid.uuid4())
        doc = Document(
            id=api_doc_id,
            filename="verify_findings.pdf",
            file_type="pdf",
            file_path="uploads/verify_findings.pdf",
            status=DocumentStatus.NORMALIZED.value,
        )
        db.add(doc)

        fin_data = FinancialData(
            id=str(uuid.uuid4()),
            document_id=api_doc_id,
            company_name="Verification Co",
            fiscal_year="2024",
            revenue=1500000.0,
            assets=3000000.0,
            liabilities=1200000.0,
            equity=1800000.0,
            normalized_data={
                "financial_data": {
                    "revenue": 1500000.0,
                    "gross_profit": 600000.0,
                    "net_profit": 250000.0,
                    "assets": 3000000.0,
                    "liabilities": 1200000.0,
                    "equity": 1800000.0,
                    "current_assets": 1000000.0,
                    "current_liabilities": 500000.0,
                    "inventory": 200000.0,
                },
                "previous_period_data": {
                    "period": "2023",
                    "financial_data": {
                        "revenue": 1200000.0,
                        "gross_profit": 480000.0,
                        "net_profit": 190000.0,
                        "assets": 2400000.0,
                        "liabilities": 1000000.0,
                        "equity": 1400000.0,
                        "current_assets": 800000.0,
                        "current_liabilities": 400000.0,
                        "inventory": 150000.0,
                    }
                }
            }
        )
        db.add(fin_data)
        db.commit()

        resp = client.post(f"/api/v1/agent1/{api_doc_id}/findings")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        payload = resp.json()
        assert payload["status"] == "COMPLETED"
        assert payload["document_id"] == api_doc_id
        assert len(payload["findings"]["validations"]) == 1
        assert payload["findings"]["validations"][0]["status"] == "VALID"
        assert len(payload["findings"]["variances"]) > 0
        assert len(payload["findings"]["anomalies"]) == 1
        assert len(payload["findings"]["ratios"]) > 0
        assert len(payload["findings"]["evidence"]) >= 9
        print("  [OK] Case 2: API POST /api/v1/agent1/{id}/findings PASSED")

        # Case 3: DB persistence check
        db.expire_all()
        refreshed = db.query(FinancialData).filter(FinancialData.document_id == api_doc_id).first()
        assert "analysis" in refreshed.normalized_data
        assert "agent1_findings" in refreshed.normalized_data["analysis"]
        persisted = refreshed.normalized_data["analysis"]["agent1_findings"]
        assert persisted["status"] == "COMPLETED"
        assert "validations" in persisted["findings"]
        print("  [OK] Case 3: Database atomic persistence PASSED")

        # Case 4: Idempotency check
        resp2 = client.post(f"/api/v1/agent1/{api_doc_id}/findings")
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "COMPLETED"
        print("  [OK] Case 4: Repeated execution (Idempotency) PASSED")

        print("==================================================")
        print("ALL VERIFICATION CHECKS PASSED: FINAL STATUS: PASS")
        print("==================================================")

    finally:
        db.close()

if __name__ == "__main__":
    run_verification()
