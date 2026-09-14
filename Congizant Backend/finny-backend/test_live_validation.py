import sys
import json
import requests
from pathlib import Path
from sqlalchemy import create_engine, text

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"

def run_live_tests():
    print("==================================================")
    print("1. HEALTH & SWAGGER VERIFICATION")
    print("==================================================")
    r_health = requests.get(f"{BASE_URL}/api/health")
    print(f"GET /api/health: {r_health.status_code}")
    assert r_health.status_code == 200

    r_docs = requests.get(f"{BASE_URL}/docs")
    print(f"GET /docs: {r_docs.status_code}")
    assert r_docs.status_code == 200

    r_openapi = requests.get(f"{BASE_URL}/openapi.json")
    print(f"GET /openapi.json: {r_openapi.status_code}")
    assert r_openapi.status_code == 200
    paths = r_openapi.json()["paths"]
    assert "/api/v1/validation/{document_id}/math" in paths
    print("Endpoint '/api/v1/validation/{document_id}/math' is present in OpenAPI schema!")

    print("\n==================================================")
    print("2. API TEST A — VALID NORMALIZED DOCUMENT")
    print("==================================================")
    # Upload and process sample_financial.csv
    with open("sample_financial.csv", "rb") as f:
        up_resp = requests.post(f"{BASE_URL}/api/v1/documents/upload", files={"file": ("sample_financial.csv", f, "text/csv")}).json()
    doc_id_valid = up_resp["document_id"]
    requests.post(f"{BASE_URL}/api/v1/documents/{doc_id_valid}/process")

    # Call math validation endpoint
    val_resp_a = requests.post(f"{BASE_URL}/api/v1/validation/{doc_id_valid}/math")
    print(f"HTTP Status: {val_resp_a.status_code}")
    data_a = val_resp_a.json()
    print(f"Response: {json.dumps(data_a, indent=2)}")
    assert val_resp_a.status_code == 200
    check_a = data_a["balance_sheet_check"]
    assert check_a["is_valid"] is True
    assert check_a["status"] == "VALID"
    assert check_a["assets"] == 45000000.0
    assert check_a["liabilities"] == 18000000.0
    assert check_a["equity"] == 27000000.0
    assert check_a["difference"] == 0.0

    print("\n==================================================")
    print("3. API TEST B — INVALID NORMALIZED DOCUMENT")
    print("==================================================")
    # Create invalid financial CSV (Assets 45M, Liabilities 20M, Equity 27M)
    inv_csv = Path("invalid_balance_sheet.csv")
    inv_csv.write_text(
        "Particulars,2025\n"
        'Total Assets,"45,000,000"\n'
        'Total Liabilities,"20,000,000"\n'
        'Shareholders\' Equity,"27,000,000"\n',
        encoding="utf-8"
    )
    with open(inv_csv, "rb") as f:
        up_inv = requests.post(f"{BASE_URL}/api/v1/documents/upload", files={"file": ("invalid_balance_sheet.csv", f, "text/csv")}).json()
    doc_id_inv = up_inv["document_id"]
    requests.post(f"{BASE_URL}/api/v1/documents/{doc_id_inv}/process")

    val_resp_b = requests.post(f"{BASE_URL}/api/v1/validation/{doc_id_inv}/math")
    print(f"HTTP Status: {val_resp_b.status_code}")
    data_b = val_resp_b.json()
    print(f"Response: {json.dumps(data_b, indent=2)}")
    assert val_resp_b.status_code == 200
    check_b = data_b["balance_sheet_check"]
    assert check_b["is_valid"] is False
    assert check_b["status"] == "INVALID"
    assert check_b["difference"] == -2000000.0
    inv_csv.unlink()

    print("\n==================================================")
    print("4. API TEST C — MISSING FINANCIAL FIELD")
    print("==================================================")
    # Create missing equity CSV
    miss_csv = Path("missing_equity.csv")
    miss_csv.write_text(
        "Particulars,2025\n"
        'Total Assets,"45,000,000"\n'
        'Total Liabilities,"18,000,000"\n',
        encoding="utf-8"
    )
    with open(miss_csv, "rb") as f:
        up_miss = requests.post(f"{BASE_URL}/api/v1/documents/upload", files={"file": ("missing_equity.csv", f, "text/csv")}).json()
    doc_id_miss = up_miss["document_id"]
    requests.post(f"{BASE_URL}/api/v1/documents/{doc_id_miss}/process")

    val_resp_c = requests.post(f"{BASE_URL}/api/v1/validation/{doc_id_miss}/math")
    print(f"HTTP Status: {val_resp_c.status_code}")
    data_c = val_resp_c.json()
    print(f"Response: {json.dumps(data_c, indent=2)}")
    assert val_resp_c.status_code == 200
    check_c = data_c["balance_sheet_check"]
    assert check_c["is_valid"] is None
    assert check_c["status"] == "INCOMPLETE"
    assert "equity" in check_c["reason"]
    miss_csv.unlink()

    print("\n==================================================")
    print("5. API TEST D — NONEXISTENT DOCUMENT")
    print("==================================================")
    val_resp_d = requests.post(f"{BASE_URL}/api/v1/validation/00000000-0000-0000-0000-000000000000/math")
    print(f"HTTP Status: {val_resp_d.status_code}")
    print(f"Response: {val_resp_d.json()}")
    assert val_resp_d.status_code == 404

    print("\n==================================================")
    print("6. API TEST E — DOCUMENT NOT NORMALIZED")
    print("==================================================")
    # Upload without processing
    unproc_csv = Path("unprocessed_test.csv")
    unproc_csv.write_text("Particulars,2025\nRevenue,100\n", encoding="utf-8")
    with open(unproc_csv, "rb") as f:
        up_unproc = requests.post(f"{BASE_URL}/api/v1/documents/upload", files={"file": ("unprocessed_test.csv", f, "text/csv")}).json()
    doc_id_unproc = up_unproc["document_id"]

    val_resp_e = requests.post(f"{BASE_URL}/api/v1/validation/{doc_id_unproc}/math")
    print(f"HTTP Status: {val_resp_e.status_code}")
    print(f"Response: {val_resp_e.json()}")
    assert val_resp_e.status_code == 400
    assert "has not been normalized yet" in val_resp_e.json()["detail"]
    unproc_csv.unlink()

    print("\n==================================================")
    print("7. DATABASE PERSISTENCE VERIFICATION")
    print("==================================================")
    from app.core.config import settings
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT d.id, d.status, f.normalized_data
            FROM documents d
            JOIN financial_data f ON d.id = f.document_id
            WHERE d.id = :doc_id
        """), {"doc_id": doc_id_valid}).mappings().first()
        print(f"Document ID: {row['id']}")
        norm_data = row['normalized_data']
        if isinstance(norm_data, str):
            norm_data = json.loads(norm_data)
        assert "validation" in norm_data
        print(f"Persisted validation block in normalized_data JSON:")
        print(json.dumps(norm_data["validation"], indent=2))
        assert norm_data["validation"]["balance_sheet_check"]["is_valid"] is True

    print("\n==================================================")
    print("8. STAGE 1 REGRESSION CHECK")
    print("==================================================")
    # 1. Upload
    with open("sample_financial.xlsx", "rb") as f:
        s1_up = requests.post(f"{BASE_URL}/api/v1/documents/upload", files={"file": ("sample_financial.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert s1_up.status_code == 201
    s1_doc_id = s1_up.json()["document_id"]
    print(f"Stage 1 Upload: 201 OK (doc_id={s1_doc_id})")

    # 2. Process
    s1_proc = requests.post(f"{BASE_URL}/api/v1/documents/{s1_doc_id}/process")
    assert s1_proc.status_code == 200
    print(f"Stage 1 Process: 200 OK (status={s1_proc.json()['status']})")

    # 3. Status
    s1_st = requests.get(f"{BASE_URL}/api/v1/documents/{s1_doc_id}")
    assert s1_st.status_code == 200
    print(f"Stage 1 Status: 200 OK (status={s1_st.json()['status']})")

    # 4. Normalized
    s1_norm = requests.get(f"{BASE_URL}/api/v1/documents/{s1_doc_id}/normalized")
    assert s1_norm.status_code == 200
    assert s1_norm.json()["financial_data"]["revenue"] == 12500000.0
    print(f"Stage 1 Normalized Data: 200 OK (revenue={s1_norm.json()['financial_data']['revenue']})")

    # 5. Health
    s1_health = requests.get(f"{BASE_URL}/api/health")
    assert s1_health.status_code == 200
    print("Stage 1 Health: 200 OK")

    print("\nALL LIVE API, DATABASE, AND STAGE 1 CHECKS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    run_live_tests()
