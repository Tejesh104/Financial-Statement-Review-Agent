import sys
import json
import uuid
import urllib.request
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

print("==================================================================")
print("STAGE 1 + STAGE 2 COMPLETE END-TO-END FINAL VERIFICATION")
print("==================================================================")

# 1. Prepare a real CSV file for upload
sample_csv_content = """XYZ Manufacturing Ltd - Annual Accounts FY 2024-25 (USD),Amount
Total Revenue,"15,000,000"
Gross Profit,"6,000,000"
Net Profit,"2,500,000"
Total Assets,"50,000,000"
Total Liabilities,"20,000,000"
Shareholders' Equity,"30,000,000"
Current Assets,"18,000,000"
Current Liabilities,"9,000,000"
Inventory,"4,500,000"
"""
temp_upload_file = Path("uploads") / "e2e_final_test.csv"
with open(temp_upload_file, "w", encoding="utf-8") as f:
    f.write(sample_csv_content)

# 2. Stage 1: Upload File
print("\n--- STEP 1: Upload Document ---")
with open(temp_upload_file, "rb") as f:
    r_upload = client.post(
        "/api/v1/documents/upload",
        files={"file": ("e2e_final_test.csv", f, "text/csv")}
    )
print(f"POST /api/v1/documents/upload: Status {r_upload.status_code}")
upload_data = r_upload.json()
doc_id = upload_data["document_id"]
print(f"Uploaded Document ID: {doc_id}, Initial Status: {upload_data['status']}")
assert r_upload.status_code == 201, f"Upload failed: {r_upload.text}"
assert upload_data["status"] == "UPLOADED"

# 3. Stage 1: Process Document (Extraction -> Normalization)
print("\n--- STEP 2: Process Document (Extraction -> Normalization) ---")
r_process = client.post(f"/api/v1/documents/{doc_id}/process")
print(f"POST /api/v1/documents/{doc_id}/process: Status {r_process.status_code}")
process_data = r_process.json()
print(f"Processed Status: {process_data['status']}")
print(f"Company: {process_data['company']['name']}")
print(f"Currency: {process_data['currency']}")
print(f"Period: {process_data['period']['fiscal_year']}")
print(f"Revenue: {process_data['financial_data']['revenue']}")
print(f"Assets: {process_data['financial_data']['assets']}")
print(f"Liabilities: {process_data['financial_data']['liabilities']}")
print(f"Equity: {process_data['financial_data']['equity']}")
assert r_process.status_code == 200
assert process_data["status"] == "NORMALIZED"

# Add previous period data to the normalized record to enable full YoY evaluation
fin_db = db.query(FinancialData).filter(FinancialData.document_id == doc_id).first()
norm_update = dict(fin_db.normalized_data or {})
norm_update["previous_period_data"] = {
    "period": "2023-24",
    "financial_data": {
        "revenue": 12000000.0,
        "gross_profit": 4800000.0,
        "net_profit": 2000000.0,
        "assets": 40000000.0,
        "liabilities": 16000000.0,
        "equity": 24000000.0,
        "current_assets": 15000000.0,
        "current_liabilities": 7500000.0,
        "inventory": 3500000.0,
    }
}
fin_db.normalized_data = norm_update
db.commit()

# 4. Stage 1: Verify Status & Normalized Data APIs
print("\n--- STEP 3: Verify Status & Normalized Data APIs ---")
r_status = client.get(f"/api/v1/documents/{doc_id}")
print(f"GET /api/v1/documents/{doc_id}: Status {r_status.status_code}, Doc Status: {r_status.json()['status']}")
assert r_status.status_code == 200
assert r_status.json()["status"] == "NORMALIZED"

r_norm = client.get(f"/api/v1/documents/{doc_id}/normalized")
print(f"GET /api/v1/documents/{doc_id}/normalized: Status {r_norm.status_code}")
assert r_norm.status_code == 200

# 5. Stage 2: Math Validation
print("\n--- STEP 4: Math Validation ---")
r_math = client.post(f"/api/v1/validation/{doc_id}/math")
print(f"POST /api/v1/validation/{doc_id}/math: Status {r_math.status_code}")
math_data = r_math.json()["balance_sheet_check"]
print(f"  Assets: {math_data['assets']}, Liabilities: {math_data['liabilities']}, Equity: {math_data['equity']}")
print(f"  Is Valid: {math_data['is_valid']}, Status: {math_data['status']}")
assert r_math.status_code == 200
assert math_data["status"] == "VALID"

# 6. Stage 2: YoY Analysis
print("\n--- STEP 5: YoY Analysis ---")
r_yoy = client.post(f"/api/v1/analysis/{doc_id}/yoy")
print(f"POST /api/v1/analysis/{doc_id}/yoy: Status {r_yoy.status_code}")
yoy_data = r_yoy.json()["yoy_analysis"]
print(f"  YoY Status: {yoy_data['status']}, Periods: {yoy_data['periods']}")
print(f"  Revenue YoY: abs={yoy_data['financial_data']['revenue']['absolute_change']}, pct={yoy_data['financial_data']['revenue']['percentage_change']}%")
assert r_yoy.status_code == 200
assert yoy_data["status"] in ["COMPLETED", "INCOMPLETE"]
assert yoy_data["financial_data"]["revenue"]["status"] == "COMPLETED"

# 7. Stage 2: Financial Ratios
print("\n--- STEP 6: Financial Ratios ---")
r_ratios = client.post(f"/api/v1/analysis/{doc_id}/ratios")
print(f"POST /api/v1/analysis/{doc_id}/ratios: Status {r_ratios.status_code}")
ratios_data = r_ratios.json()["ratio_analysis"]
print(f"  Ratio Status: {ratios_data['status']}")
r = ratios_data["ratios"]
print(f"  Current Ratio: {r['liquidity']['current_ratio']['value']}")
print(f"  Quick Ratio: {r['liquidity']['quick_ratio']['value']}")
print(f"  Gross Profit Margin: {r['profitability']['gross_profit_margin']['value']}%")
print(f"  Net Profit Margin: {r['profitability']['net_profit_margin']['value']}%")
print(f"  Return on Assets: {r['profitability']['return_on_assets']['value']}%")
print(f"  Return on Equity: {r['profitability']['return_on_equity']['value']}%")
print(f"  Debt-to-Equity: {r['leverage']['debt_to_equity']['value']}")
print(f"  Debt Ratio: {r['leverage']['debt_ratio']['value']}")
assert r_ratios.status_code == 200
assert ratios_data["status"] == "COMPLETED"

# 8. Stage 2: Agent 1 Result Builder
print("\n--- STEP 7: Agent 1 Result Builder ---")
r_agent1 = client.post(f"/api/v1/agent1/{doc_id}")
print(f"POST /api/v1/agent1/{doc_id}: Status {r_agent1.status_code}")
agent1_data = r_agent1.json()
print(f"  Agent: {agent1_data['agent']}")
print(f"  Overall Status: {agent1_data['status']}")
print(f"  Math status: {agent1_data['results']['math_validation']['status']}")
print(f"  YoY status: {agent1_data['results']['yoy_analysis']['status']}")
print(f"  Ratios status: {agent1_data['results']['financial_ratios']['status']}")
assert r_agent1.status_code == 200
assert agent1_data["status"] in ["COMPLETED", "PARTIAL"]

# 9. Stage 2: Agent 1 Alias Route
print("\n--- STEP 8: Agent 1 Alias Endpoint ---")
r_alias = client.post(f"/api/v1/analysis/{doc_id}/agent1")
print(f"POST /api/v1/analysis/{doc_id}/agent1: Status {r_alias.status_code}")
assert r_alias.status_code == 200
assert r_alias.json()["status"] in ["COMPLETED", "PARTIAL"]

# 10. Database Consistency & Persistence Verification
print("\n--- STEP 9: Database Consistency Verification ---")
db.refresh(fin_db)
persisted = fin_db.normalized_data or {}
print(f"  Has 'validation': {'validation' in persisted}")
print(f"  Has 'analysis.yoy': {'yoy' in persisted.get('analysis', {})}")
print(f"  Has 'analysis.ratios': {'ratios' in persisted.get('analysis', {})}")
print(f"  Has 'analysis.agent1': {'agent1' in persisted.get('analysis', {})}")
row_count = db.query(FinancialData).filter(FinancialData.document_id == doc_id).count()
print(f"  FinancialData rows for this doc: {row_count}")
doc_check = db.query(Document).filter(Document.id == doc_id).first()
print(f"  Document status maintained as: {doc_check.status}")
assert "validation" in persisted
assert "yoy" in persisted.get("analysis", {})
assert "ratios" in persisted.get("analysis", {})
assert "agent1" in persisted.get("analysis", {})
assert row_count == 1
assert doc_check.status == "NORMALIZED"

# 11. Idempotence / Repeated Execution
print("\n--- STEP 10: Idempotence & Repeated Execution ---")
for _ in range(2):
    client.post(f"/api/v1/validation/{doc_id}/math")
    client.post(f"/api/v1/analysis/{doc_id}/yoy")
    client.post(f"/api/v1/analysis/{doc_id}/ratios")
    client.post(f"/api/v1/agent1/{doc_id}")
row_count_after = db.query(FinancialData).filter(FinancialData.document_id == doc_id).count()
print(f"  FinancialData rows after multiple executions: {row_count_after}")
assert row_count_after == 1

# 12. Error Cases
print("\n--- STEP 11: Error Cases Check ---")
assert client.post("/api/v1/agent1/bad-uuid").status_code == 400
assert client.post(f"/api/v1/agent1/{uuid.uuid4()}").status_code == 404
print("  Invalid UUID -> 400: VERIFIED")
print("  Nonexistent UUID -> 404: VERIFIED")

print("\n==================================================================")
print("FINAL STAGE 1 + STAGE 2 E2E VERIFICATION: ALL CHECKS PASSED!")
print("==================================================================")
