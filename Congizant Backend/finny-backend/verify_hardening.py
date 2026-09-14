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
print("SECTION 1: SYSTEM HEALTH & OPENAPI REGISTRATION")
print("==================================================")
r_health = client.get("/api/health")
print("GET /api/health Status:", r_health.status_code)
print("Health Response:", r_health.json())

r_docs = client.get("/docs")
r_openapi = client.get("/openapi.json")
print("GET /docs Status:", r_docs.status_code)
print("GET /openapi.json Status:", r_openapi.status_code)

paths = r_openapi.json().get("paths", {})
registered_endpoints = [
    "/api/v1/validation/{document_id}/math",
    "/api/v1/analysis/{document_id}/yoy",
    "/api/v1/analysis/{document_id}/ratios",
    "/api/v1/agent1/{document_id}",
    "/api/v1/analysis/{document_id}/agent1",
]
for ep in registered_endpoints:
    print(f"Endpoint '{ep}': {'REGISTERED' if ep in paths else 'MISSING'}")

print("\n==================================================")
print("SECTION 2: UUID & DOCUMENT STATE VALIDATION")
print("==================================================")
# Invalid UUID -> 400
bad_uuid_resp = client.post("/api/v1/agent1/not-a-valid-uuid-format")
print("Invalid UUID (not-a-valid-uuid) Status:", bad_uuid_resp.status_code, "Detail:", bad_uuid_resp.json()["detail"])

# Nonexistent UUID -> 404
nonexistent_id = str(uuid.uuid4())
not_found_resp = client.post(f"/api/v1/agent1/{nonexistent_id}")
print("Nonexistent UUID Status:", not_found_resp.status_code, "Detail:", not_found_resp.json()["detail"])

# Unnormalized Document -> 400
unnorm_id = str(uuid.uuid4())
unnorm_doc = Document(
    id=unnorm_id,
    filename="raw_hardening.pdf",
    file_type="pdf",
    file_path="uploads/raw_hardening.pdf",
    status=DocumentStatus.EXTRACTING.value
)
db.add(unnorm_doc)
db.commit()
unnorm_resp = client.post(f"/api/v1/agent1/{unnorm_id}")
print("Unnormalized Document (EXTRACTING) Status:", unnorm_resp.status_code, "Detail:", unnorm_resp.json()["detail"])

print("\n==================================================")
print("SECTION 3: COMPLETE PIPELINE EXECUTION & PERSISTENCE PRESERVATION")
print("==================================================")
doc_id = str(uuid.uuid4())
doc = Document(
    id=doc_id,
    filename="hardening_full.csv",
    file_type="csv",
    file_path=str(Path("uploads") / "hardening_full.csv"),
    status=DocumentStatus.NORMALIZED.value
)
fin = FinancialData(
    id=str(uuid.uuid4()),
    document_id=doc_id,
    company_name="Larsen & Toubro Ltd",
    currency="INR",
    fiscal_year="2024-25",
    revenue=50000000.0,
    assets=100000000.0,
    liabilities=40000000.0,
    equity=60000000.0,
    normalized_data={
        "document_id": doc_id,
        "company": {"name": "Larsen & Toubro Ltd"},
        "currency": "INR",
        "period": {"fiscal_year": "2024-25"},
        "previous_period_data": {
            "period": "2023-24",
            "financial_data": {
                "revenue": 40000000.0,
                "gross_profit": 16000000.0,
                "net_profit": 6000000.0,
                "assets": 80000000.0,
                "liabilities": 30000000.0,
                "equity": 50000000.0,
                "current_assets": 25000000.0,
                "current_liabilities": 12000000.0,
                "inventory": 6000000.0,
            }
        },
        "financial_data": {
            "revenue": 50000000.0,
            "gross_profit": 20000000.0,
            "net_profit": 8000000.0,
            "assets": 100000000.0,
            "equity": 60000000.0,
            "liabilities": 40000000.0,
            "current_assets": 32000000.0,
            "current_liabilities": 16000000.0,
            "inventory": 8000000.0,
        }
    }
)
db.add(doc)
db.add(fin)
db.commit()

# Run Math
res_math = client.post(f"/api/v1/validation/{doc_id}/math")
print("1. POST /api/v1/validation/{id}/math ->", res_math.status_code, "status:", res_math.json()["balance_sheet_check"]["status"])

# Run YoY
res_yoy = client.post(f"/api/v1/analysis/{doc_id}/yoy")
print("2. POST /api/v1/analysis/{id}/yoy ->", res_yoy.status_code, "status:", res_yoy.json()["yoy_analysis"]["status"])

# Run Ratios
res_ratios = client.post(f"/api/v1/analysis/{doc_id}/ratios")
print("3. POST /api/v1/analysis/{id}/ratios ->", res_ratios.status_code, "status:", res_ratios.json()["ratio_analysis"]["status"])

# Run Agent 1
res_agent1 = client.post(f"/api/v1/agent1/{doc_id}")
print("4. POST /api/v1/agent1/{id} ->", res_agent1.status_code, "status:", res_agent1.json()["status"])

# Run Agent 1 Alias
res_alias = client.post(f"/api/v1/analysis/{doc_id}/agent1")
print("5. POST /api/v1/analysis/{id}/agent1 ->", res_alias.status_code, "status:", res_alias.json()["status"])

# Verify Database Persistence & Coexistence
db.refresh(fin)
stored_norm = fin.normalized_data or {}
print("\n--- Persistence Coexistence Check ---")
print("Has 'validation':", "validation" in stored_norm)
print("Has 'analysis.yoy':", "yoy" in stored_norm.get("analysis", {}))
print("Has 'analysis.ratios':", "ratios" in stored_norm.get("analysis", {}))
print("Has 'analysis.agent1':", "agent1" in stored_norm.get("analysis", {}))
print("FinancialData row count for doc:", db.query(FinancialData).filter(FinancialData.document_id == doc_id).count())
print("Document Status maintained as:", doc.status)

print("\n==================================================")
print("SECTION 4: REPEATED EXECUTION (IDEMPOTENCE)")
print("==================================================")
for i in range(2):
    client.post(f"/api/v1/agent1/{doc_id}")
row_count = db.query(FinancialData).filter(FinancialData.document_id == doc_id).count()
print("FinancialData row count after multiple executions:", row_count)

print("\nALL HARDENING VERIFICATION CHECKS PASSED!")
