"""Verification script for Step 3.3 ML Anomaly Detection live end-to-end flow."""

import sys
import json
import uuid
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.database.database import SessionLocal
from app.models.document import Document, DocumentStatus
from app.models.financial_data import FinancialData

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

client = TestClient(app)
db = SessionLocal()

print("==================================================")
print("FINNY BACKEND: STEP 3.3 ML INFERENCE VERIFICATION")
print("==================================================")

# 1. Health check & Swagger inspection
print("\n--- 1. API Health & OpenAPI Registration ---")
r_health = client.get("/api/health")
print("GET /api/health Status:", r_health.status_code)
assert r_health.status_code == 200

r_openapi = client.get("/openapi.json")
print("GET /openapi.json Status:", r_openapi.status_code)
assert r_openapi.status_code == 200
has_ml_endpoint = "/api/v1/ml/{document_id}/anomaly" in r_openapi.json().get("paths", {})
print("ML Endpoint registered in OpenAPI:", has_ml_endpoint)
assert has_ml_endpoint is True

# 2. Stage 1: Upload a real CSV file
print("\n--- 2. Stage 1: Upload Document ---")
sample_csv_content = """Alpha Manufacturing Corp - Annual Accounts FY 2023-24 (USD),Amount
Total Revenue,"25,000,000"
Gross Profit,"11,250,000"
Net Profit,"3,750,000"
Total Assets,"60,000,000"
Total Liabilities,"24,000,000"
Shareholders' Equity,"36,000,000"
Current Assets,"22,000,000"
Current Liabilities,"11,000,000"
Inventory,"5,000,000"
"""
temp_upload_file = Path("uploads") / "e2e_ml_test.csv"
temp_upload_file.parent.mkdir(parents=True, exist_ok=True)
with open(temp_upload_file, "w", encoding="utf-8") as f:
    f.write(sample_csv_content)

with open(temp_upload_file, "rb") as f:
    r_upload = client.post(
        "/api/v1/documents/upload",
        files={"file": ("e2e_ml_test.csv", f, "text/csv")}
    )
print("POST /api/v1/documents/upload Status:", r_upload.status_code)
assert r_upload.status_code == 201
doc_id = r_upload.json()["document_id"]
print("Uploaded Document ID:", doc_id)

# 3. Stage 1: Process Document (Extraction -> Normalization)
print("\n--- 3. Stage 1: Process Document ---")
r_process = client.post(f"/api/v1/documents/{doc_id}/process")
print(f"POST /api/v1/documents/{doc_id}/process Status:", r_process.status_code)
assert r_process.status_code == 200
assert r_process.json()["status"] == "NORMALIZED"

# 4. Stage 2: Execute Agent 1 Result Builder
print("\n--- 4. Stage 2: Execute Agent 1 ---")
r_agent1 = client.post(f"/api/v1/agent1/{doc_id}")
print(f"POST /api/v1/agent1/{doc_id} Status:", r_agent1.status_code)
assert r_agent1.status_code == 200
agent1_body = r_agent1.json()
print("Agent 1 Status:", agent1_body["status"])

# 5. Step 3.3: Execute ML Anomaly Detection Endpoint
print("\n--- 5. Step 3.3: Execute ML Anomaly Detection ---")
r_ml = client.post(f"/api/v1/ml/{doc_id}/anomaly")
print(f"POST /api/v1/ml/{doc_id}/anomaly Status:", r_ml.status_code)
assert r_ml.status_code == 200
ml_body = r_ml.json()
print("\nML Response:")
print(json.dumps(ml_body, indent=2))

assert ml_body["status"] in ("COMPLETED", "INCOMPLETE")
assert "anomaly_detection" in ml_body
assert "prediction" in ml_body["anomaly_detection"]
assert "score" in ml_body["anomaly_detection"]
assert "label" in ml_body["anomaly_detection"]
assert ml_body["anomaly_detection"]["label"] in ("normal", "anomaly")

# 6. Database Persistence Verification
print("\n--- 6. Database Persistence Verification ---")
fin_db = db.query(FinancialData).filter(FinancialData.document_id == doc_id).first()
db.refresh(fin_db)
persisted = fin_db.normalized_data or {}
print("Has 'validation':", "validation" in persisted)
print("Has 'analysis.yoy':", "yoy" in persisted.get("analysis", {}))
print("Has 'analysis.ratios':", "ratios" in persisted.get("analysis", {}))
print("Has 'analysis.agent1':", "agent1" in persisted.get("analysis", {}))
print("Has 'ml_anomaly':", "ml_anomaly" in persisted)

assert "ml_anomaly" in persisted
assert persisted["ml_anomaly"]["anomaly_detection"]["prediction"] == ml_body["anomaly_detection"]["prediction"]
assert persisted["ml_anomaly"]["anomaly_detection"]["score"] == ml_body["anomaly_detection"]["score"]

# 7. Idempotence / Repeated Execution
print("\n--- 7. Idempotence & Repeated Execution ---")
r_ml_repeat = client.post(f"/api/v1/ml/{doc_id}/anomaly")
print(f"Repeated POST /api/v1/ml/{doc_id}/anomaly Status:", r_ml_repeat.status_code)
assert r_ml_repeat.status_code == 200
assert r_ml_repeat.json()["anomaly_detection"]["score"] == ml_body["anomaly_detection"]["score"]

row_count = db.query(FinancialData).filter(FinancialData.document_id == doc_id).count()
print(f"FinancialData row count after repeated execution: {row_count}")
assert row_count == 1

doc_check = db.query(Document).filter(Document.id == doc_id).first()
print(f"Document status maintained as: {doc_check.status}")
assert doc_check.status == "NORMALIZED"

# 8. Clean up temporary test file
if temp_upload_file.exists():
    temp_upload_file.unlink()

print("\n==================================================")
print("STEP 3.3 ML INFERENCE VERIFICATION: ALL CHECKS PASSED!")
print("==================================================")
