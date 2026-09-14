import sys
import json
import requests
from pathlib import Path
from sqlalchemy import create_engine, text

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"

def main():
    print("==================================================")
    print("SECTION 5: API VERIFICATION WITH REAL NORMALIZED DOCUMENT")
    print("==================================================")
    # 1. Health check
    r_health = requests.get(f"{BASE_URL}/api/health")
    print(f"GET /api/health Status: {r_health.status_code}")
    print(f"Health Response: {r_health.json()}")
    assert r_health.status_code == 200

    # 2. Upload real document
    with open("sample_financial.csv", "rb") as f:
        up_resp = requests.post(
            f"{BASE_URL}/api/v1/documents/upload",
            files={"file": ("sample_financial.csv", f, "text/csv")}
        )
    assert up_resp.status_code == 201
    doc_id = up_resp.json()["document_id"]
    print(f"Document Uploaded: ID={doc_id}")

    # 3. Process document through Stage 1 pipeline
    proc_resp = requests.post(f"{BASE_URL}/api/v1/documents/{doc_id}/process")
    assert proc_resp.status_code == 200
    print(f"Document Processed to NORMALIZED: {proc_resp.json()['status']}")

    # 4. Call mathematical validation endpoint
    val_resp = requests.post(f"{BASE_URL}/api/v1/validation/{doc_id}/math")
    print(f"\nPOST /api/v1/validation/{doc_id}/math Status: {val_resp.status_code}")
    val_data = val_resp.json()
    print("COMPLETE HTTP RESPONSE BODY:")
    print(json.dumps(val_data, indent=2))
    assert val_resp.status_code == 200

    check = val_data["balance_sheet_check"]
    assert val_data["document_id"] == doc_id
    assert check["assets"] == 45000000.0
    assert check["liabilities"] == 18000000.0
    assert check["equity"] == 27000000.0
    assert check["liabilities_plus_equity"] == 45000000.0
    assert check["difference"] == 0.0
    assert check["tolerance"] == 0.01
    assert check["is_valid"] is True
    assert check["status"] == "VALID"

    print("\n==================================================")
    print("SECTION 6: API ERROR CASES")
    print("==================================================")
    # A. Nonexistent document ID
    non_existent_id = "00000000-0000-0000-0000-000000000000"
    r_err_a = requests.post(f"{BASE_URL}/api/v1/validation/{non_existent_id}/math")
    print(f"A. Nonexistent document ID ({non_existent_id}):")
    print(f"   Status Code: {r_err_a.status_code}")
    print(f"   Response Body: {r_err_a.json()}")
    assert r_err_a.status_code == 404

    # B. Document that has not been normalized (UPLOADED status only)
    temp_unproc = Path("temp_unproc.csv")
    temp_unproc.write_text("Particulars,2025\nRevenue,1000\n", encoding="utf-8")
    with open(temp_unproc, "rb") as f:
        up_unproc = requests.post(f"{BASE_URL}/api/v1/documents/upload", files={"file": ("temp_unproc.csv", f, "text/csv")}).json()
    unproc_id = up_unproc["document_id"]

    r_err_b = requests.post(f"{BASE_URL}/api/v1/validation/{unproc_id}/math")
    print(f"\nB. Document not normalized (status=UPLOADED, ID={unproc_id}):")
    print(f"   Status Code: {r_err_b.status_code}")
    print(f"   Response Body: {r_err_b.json()}")
    assert r_err_b.status_code == 400
    temp_unproc.unlink()

    # C. Normalized document with missing financial data (e.g. missing equity)
    temp_missing = Path("temp_missing.csv")
    temp_missing.write_text(
        "Particulars,2025\n"
        'Total Assets,"45,000,000"\n'
        'Total Liabilities,"18,000,000"\n',
        encoding="utf-8"
    )
    with open(temp_missing, "rb") as f:
        up_missing = requests.post(f"{BASE_URL}/api/v1/documents/upload", files={"file": ("temp_missing.csv", f, "text/csv")}).json()
    missing_id = up_missing["document_id"]
    requests.post(f"{BASE_URL}/api/v1/documents/{missing_id}/process")

    r_err_c = requests.post(f"{BASE_URL}/api/v1/validation/{missing_id}/math")
    print(f"\nC. Normalized document with missing equity (ID={missing_id}):")
    print(f"   Status Code: {r_err_c.status_code}")
    print(f"   Response Body: {r_err_c.json()}")
    assert r_err_c.status_code == 200
    assert r_err_c.json()["balance_sheet_check"]["status"] == "INCOMPLETE"
    assert r_err_c.json()["balance_sheet_check"]["is_valid"] is None
    temp_missing.unlink()

    print("\n==================================================")
    print("SECTION 7: STAGE 1 REGRESSION")
    print("==================================================")
    # 1. Upload Excel
    with open("sample_financial.xlsx", "rb") as f:
        r_up = requests.post(f"{BASE_URL}/api/v1/documents/upload", files={"file": ("sample_financial.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert r_up.status_code == 201
    s1_id = r_up.json()["document_id"]
    print(f"POST /api/v1/documents/upload: Status {r_up.status_code} (document_id={s1_id})")

    # 2. Process
    r_proc = requests.post(f"{BASE_URL}/api/v1/documents/{s1_id}/process")
    assert r_proc.status_code == 200
    print(f"POST /api/v1/documents/{s1_id}/process: Status {r_proc.status_code}")

    # 3. Document status
    r_stat = requests.get(f"{BASE_URL}/api/v1/documents/{s1_id}")
    assert r_stat.status_code == 200
    print(f"GET /api/v1/documents/{s1_id}: Status {r_stat.status_code}, status={r_stat.json()['status']}")

    # 4. Normalized data
    r_norm = requests.get(f"{BASE_URL}/api/v1/documents/{s1_id}/normalized")
    assert r_norm.status_code == 200
    print(f"GET /api/v1/documents/{s1_id}/normalized: Status {r_norm.status_code}, revenue={r_norm.json()['financial_data']['revenue']}")

    # 5. Health check
    r_h = requests.get(f"{BASE_URL}/api/health")
    assert r_h.status_code == 200
    print(f"GET /api/health: Status {r_h.status_code}")

    print("\n==================================================")
    print("SECTION 8: SWAGGER VERIFICATION")
    print("==================================================")
    r_docs = requests.get(f"{BASE_URL}/docs")
    print(f"GET http://127.0.0.1:8000/docs Status: {r_docs.status_code}")
    assert r_docs.status_code == 200

    r_openapi = requests.get(f"{BASE_URL}/openapi.json")
    print(f"GET http://127.0.0.1:8000/openapi.json Status: {r_openapi.status_code}")
    assert r_openapi.status_code == 200
    paths = r_openapi.json()["paths"]
    assert "/api/v1/validation/{document_id}/math" in paths
    print("Confirmed: /api/v1/validation/{document_id}/math is registered in OpenAPI documentation!")

    print("\n==================================================")
    print("SECTION 9: DATABASE PERSISTENCE VERIFICATION")
    print("==================================================")
    from app.core.config import settings
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT d.id, d.filename, d.status, f.normalized_data
            FROM documents d
            JOIN financial_data f ON d.id = f.document_id
            WHERE d.id = :doc_id
        """), {"doc_id": doc_id}).mappings().first()

        print(f"Table: financial_data (joined to documents on documents.id = financial_data.document_id)")
        print(f"Document ID: {row['id']}")
        print(f"Document Status: {row['status']}")
        stored_norm = row['normalized_data']
        if isinstance(stored_norm, str):
            stored_norm = json.loads(stored_norm)
        print("Stored Validation Block in normalized_data JSON:")
        print(json.dumps(stored_norm.get("validation"), indent=2))
        assert stored_norm["validation"]["balance_sheet_check"]["is_valid"] is True
        assert stored_norm["validation"]["balance_sheet_check"]["status"] == "VALID"

    print("\nALL VERIFICATION SECTIONS EXECUTED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
