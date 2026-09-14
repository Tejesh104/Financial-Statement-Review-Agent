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
print("SECTION 1: HEALTH CHECK")
print("==================================================")
r_health = client.get("/api/health")
print("GET /api/health Status:", r_health.status_code)
print("Health Response:", r_health.json())

print("\n==================================================")
print("SECTION 2: POST /api/v1/agent1/{document_id} WITH COMPLETE NORMALIZED DATA")
print("==================================================")
doc_id = str(uuid.uuid4())
doc = Document(
    id=doc_id,
    filename="comprehensive_agent1_test.csv",
    file_type="csv",
    file_path=str(Path("uploads") / "comprehensive_agent1_test.csv"),
    status=DocumentStatus.NORMALIZED.value
)
fin = FinancialData(
    id=str(uuid.uuid4()),
    document_id=doc_id,
    company_name="State Bank of India",
    currency="INR",
    fiscal_year="2024-25",
    revenue=12000000.0,
    assets=30000000.0,
    liabilities=12000000.0,
    equity=18000000.0,
    normalized_data={
        "document_id": doc_id,
        "company": {"name": "State Bank of India"},
        "currency": "INR",
        "period": {"fiscal_year": "2024-25"},
        "previous_period_data": {
            "period": "2023-24",
            "financial_data": {
                "revenue": 10000000.0,
                "gross_profit": 4000000.0,
                "net_profit": 1500000.0,
                "assets": 25000000.0,
                "liabilities": 10000000.0,
                "equity": 15000000.0,
                "current_assets": 7000000.0,
                "current_liabilities": 3500000.0,
                "inventory": 1000000.0,
            }
        },
        "financial_data": {
            "revenue": 12000000.0,
            "gross_profit": 5000000.0,
            "net_profit": 2000000.0,
            "assets": 30000000.0,
            "equity": 18000000.0,
            "liabilities": 12000000.0,
            "current_assets": 9000000.0,
            "current_liabilities": 4500000.0,
            "inventory": 1500000.0,
        }
    }
)
db.add(doc)
db.add(fin)
db.commit()

resp = client.post(f"/api/v1/agent1/{doc_id}")
print("POST /api/v1/agent1/{document_id} Status:", resp.status_code)
print("COMPLETE HTTP RESPONSE BODY:")
print(json.dumps(resp.json(), indent=2))

print("\n==================================================")
print("SECTION 3: ALIAS ENDPOINT /api/v1/analysis/{document_id}/agent1")
print("==================================================")
resp_alias = client.post(f"/api/v1/analysis/{doc_id}/agent1")
print("POST /api/v1/analysis/{document_id}/agent1 Status:", resp_alias.status_code)
print("Alias Response matches doc_id:", resp_alias.json()["document_id"] == doc_id)

print("\n==================================================")
print("SECTION 4: ERROR & EDGE CASES")
print("==================================================")
r_404 = client.post(f"/api/v1/agent1/{uuid.uuid4()}")
print("A. Nonexistent Document Status:", r_404.status_code, "Body:", r_404.json())

unnorm_id = str(uuid.uuid4())
unnorm_doc = Document(
    id=unnorm_id,
    filename="raw_agent1.pdf",
    file_type="pdf",
    file_path="uploads/raw_agent1.pdf",
    status=DocumentStatus.UPLOADED.value
)
db.add(unnorm_doc)
db.commit()
r_400 = client.post(f"/api/v1/agent1/{unnorm_id}")
print("B. Unnormalized Document Status:", r_400.status_code, "Body:", r_400.json())

print("\n==================================================")
print("SECTION 5: SWAGGER & OPENAPI DOCUMENTATION")
print("==================================================")
r_docs = client.get("/docs")
r_openapi = client.get("/openapi.json")
print("GET /docs Status:", r_docs.status_code)
print("GET /openapi.json Status:", r_openapi.status_code)
paths = r_openapi.json().get("paths", {})
has_agent1 = "/api/v1/agent1/{document_id}" in paths
has_alias = "/api/v1/analysis/{document_id}/agent1" in paths
print("Agent 1 Primary Endpoint in OpenAPI:", has_agent1)
print("Agent 1 Alias Endpoint in OpenAPI:", has_alias)
print("Existing Math in OpenAPI:", "/api/v1/validation/{document_id}/math" in paths)
print("Existing YoY in OpenAPI:", "/api/v1/analysis/{document_id}/yoy" in paths)
print("Existing Ratios in OpenAPI:", "/api/v1/analysis/{document_id}/ratios" in paths)

print("\n==================================================")
print("SECTION 6: DATABASE PERSISTENCE VERIFICATION")
print("==================================================")
db.refresh(fin)
stored_norm = fin.normalized_data or {}
agent1_block = stored_norm.get("analysis", {}).get("agent1")
print("Persisted in financial_data.normalized_data['analysis']['agent1']:")
print("Status:", agent1_block.get("status") if agent1_block else None)
print("Agent:", agent1_block.get("agent") if agent1_block else None)
print("Has Math Validation:", "math_validation" in agent1_block.get("results", {}))
print("Has YoY Analysis:", "yoy_analysis" in agent1_block.get("results", {}))
print("Has Financial Ratios:", "financial_ratios" in agent1_block.get("results", {}))

print("\nALL AGENT 1 API VERIFICATION STEPS COMPLETED!")
