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
print("SECTION 2: POST /api/v1/analysis/{document_id}/ratios WITH COMPLETE NORMALIZED DATA")
print("==================================================")
doc_id = str(uuid.uuid4())
doc = Document(
    id=doc_id,
    filename="comprehensive_financials.csv",
    file_type="csv",
    file_path=str(Path("uploads") / "comprehensive_financials.csv"),
    status=DocumentStatus.NORMALIZED.value
)
fin = FinancialData(
    id=str(uuid.uuid4()),
    document_id=doc_id,
    company_name="Reliance Retail Ventures Ltd",
    currency="INR",
    fiscal_year="2024-25",
    revenue=10000000.0,
    assets=20000000.0,
    liabilities=8000000.0,
    equity=12000000.0,
    normalized_data={
        "document_id": doc_id,
        "company": {"name": "Reliance Retail Ventures Ltd"},
        "currency": "INR",
        "period": {"fiscal_year": "2024-25"},
        "financial_data": {
            "revenue": 10000000.0,
            "gross_profit": 4000000.0,
            "net_profit": 1500000.0,
            "assets": 20000000.0,
            "equity": 12000000.0,
            "liabilities": 8000000.0,
            "current_assets": 6000000.0,
            "current_liabilities": 3000000.0,
            "inventory": 1500000.0,
        }
    }
)
db.add(doc)
db.add(fin)
db.commit()

resp = client.post(f"/api/v1/analysis/{doc_id}/ratios")
print("POST /api/v1/analysis/{document_id}/ratios Status:", resp.status_code)
print("COMPLETE HTTP RESPONSE BODY:")
print(json.dumps(resp.json(), indent=2))

print("\n==================================================")
print("SECTION 3: ERROR & EDGE CASES")
print("==================================================")
r_404 = client.post(f"/api/v1/analysis/{uuid.uuid4()}/ratios")
print("A. Nonexistent Document Status:", r_404.status_code, "Body:", r_404.json())

unnorm_id = str(uuid.uuid4())
unnorm_doc = Document(
    id=unnorm_id,
    filename="raw_ratio.pdf",
    file_type="pdf",
    file_path="uploads/raw_ratio.pdf",
    status=DocumentStatus.UPLOADED.value
)
db.add(unnorm_doc)
db.commit()
r_400 = client.post(f"/api/v1/analysis/{unnorm_id}/ratios")
print("B. Unnormalized Document Status:", r_400.status_code, "Body:", r_400.json())

# Zero denominator
zero_id = str(uuid.uuid4())
zero_doc = Document(
    id=zero_id,
    filename="zero_rev_ratio.csv",
    file_type="csv",
    file_path="uploads/zero_rev_ratio.csv",
    status=DocumentStatus.NORMALIZED.value
)
zero_fin = FinancialData(
    id=str(uuid.uuid4()),
    document_id=zero_id,
    company_name="Zero Rev Ltd",
    currency="USD",
    revenue=0.0,
    assets=10000000.0,
    liabilities=4000000.0,
    equity=6000000.0,
    normalized_data={
        "document_id": zero_id,
        "financial_data": {
            "revenue": 0.0,
            "gross_profit": 500000.0,
            "assets": 10000000.0,
            "equity": 6000000.0,
        }
    }
)
db.add(zero_doc)
db.add(zero_fin)
db.commit()
r_zero = client.post(f"/api/v1/analysis/{zero_id}/ratios")
print("C. Zero Revenue GPM Status:", r_zero.status_code, "GPM:", r_zero.json()["ratio_analysis"]["ratios"]["profitability"]["gross_profit_margin"])

print("\n==================================================")
print("SECTION 4: SWAGGER & OPENAPI DOCUMENTATION")
print("==================================================")
r_docs = client.get("/docs")
r_openapi = client.get("/openapi.json")
print("GET /docs Status:", r_docs.status_code)
print("GET /openapi.json Status:", r_openapi.status_code)
paths = r_openapi.json().get("paths", {})
has_ratios = "/api/v1/analysis/{document_id}/ratios" in paths
print("Ratios Endpoint in OpenAPI:", has_ratios)

print("\n==================================================")
print("SECTION 5: DATABASE PERSISTENCE VERIFICATION")
print("==================================================")
db.refresh(fin)
stored_norm = fin.normalized_data or {}
ratios_block = stored_norm.get("analysis", {}).get("ratios")
print("Persisted in financial_data.normalized_data['analysis']['ratios']:")
print(json.dumps(ratios_block, indent=2))

print("\nALL RATIOS VERIFICATION STEPS COMPLETED!")
