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
print("SECTION 2: POST /api/v1/analysis/{document_id}/yoy WITH REAL NORMALIZED DATA")
print("==================================================")
doc_id = str(uuid.uuid4())
doc = Document(
    id=doc_id,
    filename="annual_report_2025.csv",
    file_type="csv",
    file_path=str(Path("uploads") / "annual_report_2025.csv"),
    status=DocumentStatus.NORMALIZED.value
)
fin = FinancialData(
    id=str(uuid.uuid4()),
    document_id=doc_id,
    company_name="Reliance Retail Ventures Ltd",
    currency="INR",
    fiscal_year="2024-25",
    revenue=12500000.0,
    assets=45000000.0,
    liabilities=18000000.0,
    equity=27000000.0,
    normalized_data={
        "document_id": doc_id,
        "company": {"name": "Reliance Retail Ventures Ltd"},
        "currency": "INR",
        "period": {"fiscal_year": "2024-25"},
        "financial_data": {
            "revenue": 12500000.0,
            "assets": 45000000.0,
            "liabilities": 18000000.0,
            "equity": 27000000.0
        },
        "previous_period_data": {
            "fiscal_year": "2023-24",
            "financial_data": {
                "revenue": 10000000.0,
                "assets": 40000000.0,
                "liabilities": 15000000.0,
                "equity": 25000000.0
            }
        }
    }
)
db.add(doc)
db.add(fin)
db.commit()

resp = client.post(f"/api/v1/analysis/{doc_id}/yoy")
print("POST /api/v1/analysis/{document_id}/yoy Status:", resp.status_code)
print("COMPLETE HTTP RESPONSE BODY:")
print(json.dumps(resp.json(), indent=2))

print("\n==================================================")
print("SECTION 3: ERROR & EDGE CASES")
print("==================================================")
# Nonexistent doc
r_404 = client.post(f"/api/v1/analysis/{uuid.uuid4()}/yoy")
print("A. Nonexistent Document Status:", r_404.status_code, "Body:", r_404.json())

# Unnormalized doc
unnorm_id = str(uuid.uuid4())
unnorm_doc = Document(
    id=unnorm_id,
    filename="raw_upload.pdf",
    file_type="pdf",
    file_path="uploads/raw_upload.pdf",
    status=DocumentStatus.UPLOADED.value
)
db.add(unnorm_doc)
db.commit()
r_400 = client.post(f"/api/v1/analysis/{unnorm_id}/yoy")
print("B. Unnormalized Document Status:", r_400.status_code, "Body:", r_400.json())

# One period only
single_id = str(uuid.uuid4())
single_doc = Document(
    id=single_id,
    filename="single_period.csv",
    file_type="csv",
    file_path="uploads/single_period.csv",
    status=DocumentStatus.NORMALIZED.value
)
single_fin = FinancialData(
    id=str(uuid.uuid4()),
    document_id=single_id,
    company_name="Single Year Corp",
    currency="INR",
    fiscal_year="2024-25",
    revenue=10000000.0,
    assets=30000000.0,
    liabilities=10000000.0,
    equity=20000000.0,
    normalized_data={
        "document_id": single_id,
        "company": {"name": "Single Year Corp"},
        "period": {"fiscal_year": "2024-25"},
        "financial_data": {
            "revenue": 10000000.0,
            "assets": 30000000.0,
            "liabilities": 10000000.0,
            "equity": 20000000.0
        }
    }
)
db.add(single_doc)
db.add(single_fin)
db.commit()
r_single = client.post(f"/api/v1/analysis/{single_id}/yoy")
print("C. Single Period Status:", r_single.status_code, "Body:", r_single.json())

# Zero previous
zero_id = str(uuid.uuid4())
zero_doc = Document(
    id=zero_id,
    filename="zero_prev.csv",
    file_type="csv",
    file_path="uploads/zero_prev.csv",
    status=DocumentStatus.NORMALIZED.value
)
zero_fin = FinancialData(
    id=str(uuid.uuid4()),
    document_id=zero_id,
    company_name="Zero Previous Inc",
    currency="USD",
    fiscal_year="2024-25",
    revenue=500000.0,
    assets=1000000.0,
    liabilities=400000.0,
    equity=600000.0,
    normalized_data={
        "document_id": zero_id,
        "company": {"name": "Zero Previous Inc"},
        "period": {"fiscal_year": "2024-25"},
        "financial_data": {"revenue": 500000.0, "assets": 1000000.0, "liabilities": 400000.0, "equity": 600000.0},
        "previous_period_data": {
            "fiscal_year": "2023-24",
            "financial_data": {"revenue": 0.0, "assets": 1000000.0, "liabilities": 400000.0, "equity": 600000.0}
        }
    }
)
db.add(zero_doc)
db.add(zero_fin)
db.commit()
r_zero = client.post(f"/api/v1/analysis/{zero_id}/yoy")
print("D. Zero Previous Status:", r_zero.status_code, "Revenue YoY:", r_zero.json()["yoy_analysis"]["financial_data"]["revenue"])

print("\n==================================================")
print("SECTION 4: SWAGGER & OPENAPI DOCUMENTATION")
print("==================================================")
r_docs = client.get("/docs")
r_openapi = client.get("/openapi.json")
print("GET /docs Status:", r_docs.status_code)
print("GET /openapi.json Status:", r_openapi.status_code)
paths = r_openapi.json().get("paths", {})
has_yoy = "/api/v1/analysis/{document_id}/yoy" in paths
print("YoY Endpoint in OpenAPI:", has_yoy)

print("\n==================================================")
print("SECTION 5: DATABASE PERSISTENCE VERIFICATION")
print("==================================================")
db.refresh(fin)
stored_norm = fin.normalized_data or {}
yoy_block = stored_norm.get("analysis", {}).get("yoy")
print("Persisted in financial_data.normalized_data['analysis']['yoy']:")
print(json.dumps(yoy_block, indent=2))

print("\nALL VERIFICATION STEPS COMPLETED!")
