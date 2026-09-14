import json
import sys
import requests
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
import pandas as pd
import openpyxl
import pymupdf as fitz
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.services.normalization.field_mapper import FieldMapper
from app.services.normalization.value_cleaner import ValueCleaner
from app.services.normalization.currency_normalizer import CurrencyNormalizer
from app.services.normalization.date_normalizer import DateNormalizer
from app.models.document import Document
from app.models.financial_data import FinancialData

BASE_URL = "http://127.0.0.1:8000"

def run_all_steps():
    print("==================================================")
    print("STEP 4 — TEST HEALTH ENDPOINT")
    print("==================================================")
    r = requests.get(f"{BASE_URL}/api/health")
    print(f"Status Code: {r.status_code}")
    print(f"Response: {json.dumps(r.json(), indent=2)}")
    assert r.status_code == 200

    print("\n==================================================")
    print("STEP 5 — CREATE REAL SAMPLE FILES")
    print("==================================================")
    # 1. CSV
    csv_path = Path("sample_financial.csv")
    csv_content = (
        'ABC Limited - Statement of Accounts FY 2024-25 (INR),Amount\n'
        'Total Revenue,"12,500,000"\n'
        'Total Assets,"45,000,000"\n'
        'Total Liabilities,"18,000,000"\n'
        'Shareholders\' Equity,"27,000,000"\n'
    )
    csv_path.write_text(csv_content, encoding="utf-8")
    print(f"Created: {csv_path.resolve()}")

    # 2. Excel
    xlsx_path = Path("sample_financial.xlsx")
    excel_df = pd.DataFrame({
        "Particulars": ["Revenue", "Total Assets", "Total Liabilities", "Owners' Equity"],
        "FY 2024-25 (₹)": ["12,500,000", "45,000,000", "18,000,000", "27,000,000"]
    })
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        excel_df.to_excel(writer, sheet_name="Financials", index=False)
    
    wb = openpyxl.load_workbook(xlsx_path)
    ws = wb["Financials"]
    ws.insert_rows(1)
    ws.cell(row=1, column=1, value="ABC Limited")
    ws.cell(row=1, column=2, value="INR")
    wb.save(xlsx_path)
    print(f"Created: {xlsx_path.resolve()}")

    # 3. PDF
    pdf_path = Path("sample_financial.pdf")
    doc = fitz.open()
    page = doc.new_page()
    pdf_text = (
        "ABC Limited\n"
        "Financial Statement for FY 2024-25\n"
        "Currency: INR (₹)\n\n"
        "Particulars                     FY 2024-25\n"
        "Turnover                        12,500,000\n"
        "Total Assets                    45,000,000\n"
        "Total Liabilities               18,000,000\n"
        "Shareholders Equity             27,000,000\n"
    )
    page.insert_text((50, 72), pdf_text, fontsize=12)
    doc.save(str(pdf_path))
    doc.close()
    print(f"Created: {pdf_path.resolve()}")

    print("\n==================================================")
    print("STEP 6 — TEST CSV")
    print("==================================================")
    with open(csv_path, "rb") as f:
        up_csv = requests.post(f"{BASE_URL}/api/v1/documents/upload", files={"file": ("sample_financial.csv", f, "text/csv")})
    print(f"Upload Status: {up_csv.status_code}")
    csv_upload_data = up_csv.json()
    print(f"Upload Response: {json.dumps(csv_upload_data, indent=2)}")
    csv_doc_id = csv_upload_data["document_id"]

    proc_csv = requests.post(f"{BASE_URL}/api/v1/documents/{csv_doc_id}/process")
    print(f"Process Status: {proc_csv.status_code}")
    print(f"Process Response: {json.dumps(proc_csv.json(), indent=2)}")

    status_csv = requests.get(f"{BASE_URL}/api/v1/documents/{csv_doc_id}")
    print(f"Document Status Endpoint: {json.dumps(status_csv.json(), indent=2)}")

    norm_csv = requests.get(f"{BASE_URL}/api/v1/documents/{csv_doc_id}/normalized")
    print(f"Normalized Data Endpoint: {json.dumps(norm_csv.json(), indent=2)}")
    csv_final = norm_csv.json()

    print("\n==================================================")
    print("STEP 7 — TEST EXCEL")
    print("==================================================")
    with open(xlsx_path, "rb") as f:
        up_xlsx = requests.post(f"{BASE_URL}/api/v1/documents/upload", files={"file": ("sample_financial.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    print(f"Upload Status: {up_xlsx.status_code}")
    xlsx_upload_data = up_xlsx.json()
    print(f"Upload Response: {json.dumps(xlsx_upload_data, indent=2)}")
    xlsx_doc_id = xlsx_upload_data["document_id"]

    proc_xlsx = requests.post(f"{BASE_URL}/api/v1/documents/{xlsx_doc_id}/process")
    print(f"Process Status: {proc_xlsx.status_code}")
    print(f"Process Response: {json.dumps(proc_xlsx.json(), indent=2)}")

    status_xlsx = requests.get(f"{BASE_URL}/api/v1/documents/{xlsx_doc_id}")
    print(f"Document Status Endpoint: {json.dumps(status_xlsx.json(), indent=2)}")

    norm_xlsx = requests.get(f"{BASE_URL}/api/v1/documents/{xlsx_doc_id}/normalized")
    print(f"Normalized Data Endpoint: {json.dumps(norm_xlsx.json(), indent=2)}")
    xlsx_final = norm_xlsx.json()

    print("\n==================================================")
    print("STEP 8 — TEST PDF")
    print("==================================================")
    with open(pdf_path, "rb") as f:
        up_pdf = requests.post(f"{BASE_URL}/api/v1/documents/upload", files={"file": ("sample_financial.pdf", f, "application/pdf")})
    print(f"Upload Status: {up_pdf.status_code}")
    pdf_upload_data = up_pdf.json()
    print(f"Upload Response: {json.dumps(pdf_upload_data, indent=2)}")
    pdf_doc_id = pdf_upload_data["document_id"]

    proc_pdf = requests.post(f"{BASE_URL}/api/v1/documents/{pdf_doc_id}/process")
    print(f"Process Status: {proc_pdf.status_code}")
    print(f"Process Response: {json.dumps(proc_pdf.json(), indent=2)}")

    status_pdf = requests.get(f"{BASE_URL}/api/v1/documents/{pdf_doc_id}")
    print(f"Document Status Endpoint: {json.dumps(status_pdf.json(), indent=2)}")

    norm_pdf = requests.get(f"{BASE_URL}/api/v1/documents/{pdf_doc_id}/normalized")
    print(f"Normalized Data Endpoint: {json.dumps(norm_pdf.json(), indent=2)}")
    pdf_final = norm_pdf.json()

    print("\n==================================================")
    print("STEP 9 — COMPARE ALL THREE FORMATS")
    print("==================================================")
    print(f"{'Field':<25} | {'CSV Value':<18} | {'Excel Value':<18} | {'PDF Value':<18} | {'Match?':<6}")
    print("-" * 92)
    for field in ["revenue", "assets", "liabilities", "equity"]:
        c = csv_final["financial_data"][field]
        e = xlsx_final["financial_data"][field]
        p = pdf_final["financial_data"][field]
        match = (c == e == p)
        print(f"{field:<25} | {str(c):<18} | {str(e):<18} | {str(p):<18} | {str(match):<6}")

    for meta in ["currency", "fiscal_year", "company_name"]:
        if meta == "currency":
            c, e, p = csv_final.get("currency"), xlsx_final.get("currency"), pdf_final.get("currency")
        elif meta == "fiscal_year":
            c = csv_final.get("period", {}).get("fiscal_year")
            e = xlsx_final.get("period", {}).get("fiscal_year")
            p = pdf_final.get("period", {}).get("fiscal_year")
        else:
            c = csv_final.get("company", {}).get("name")
            e = xlsx_final.get("company", {}).get("name")
            p = pdf_final.get("company", {}).get("name")
        match = (c == e == p)
        print(f"{meta:<25} | {str(c):<18} | {str(e):<18} | {str(p):<18} | {str(match):<6}")

    print("\n==================================================")
    print("STEP 10 — TEST NORMALIZATION (NUMERIC & FIELDS)")
    print("==================================================")
    # Numeric normalization
    test_nums = ["12,500,000", "₹12,500,000", "(5,000,000)", "12.5M", "10 Cr"]
    for raw in test_nums:
        val, warn = ValueCleaner.clean_numeric(raw)
        print(f"Raw: {raw:<15} -> Normalized: {val:<15} (Warning: {warn})")

    # Field name normalization
    field_mapper = FieldMapper()
    rev_variants = ["Revenue", "Total Revenue", "Net Sales", "Sales", "Turnover"]
    print("\nField Variants for Revenue:")
    for v in rev_variants:
        print(f"  '{v}' -> '{field_mapper.map_field(v)}'")

    print("\nField Variants for Assets:")
    for v in ["Assets", "Total Assets"]:
        print(f"  '{v}' -> '{field_mapper.map_field(v)}'")

    print("\nField Variants for Liabilities:")
    for v in ["Liabilities", "Total Liabilities"]:
        print(f"  '{v}' -> '{field_mapper.map_field(v)}'")

    print("\nField Variants for Equity:")
    for v in ["Equity", "Shareholders' Equity", "Shareholders Equity"]:
        print(f"  '{v}' -> '{field_mapper.map_field(v)}'")

    print("\n==================================================")
    print("STEP 11 — TEST DATE NORMALIZATION")
    print("==================================================")
    date_norm = DateNormalizer()
    dates_to_test = ["31-03-2025", "31/03/2025", "March 31, 2025", "31 March 2025", "2025-03-31", "FY 2024-25"]
    for d in dates_to_test:
        iso = date_norm.parse_iso_date(d)
        fy = date_norm.extract_fiscal_year(d)
        period = date_norm.normalize_period(d)
        print(f"Input: {d:<18} -> ISO: {str(iso):<12} FY: {str(fy):<10} Period: {period.model_dump()}")

    print("\n==================================================")
    print("STEP 12 — TEST CURRENCY NORMALIZATION")
    print("==================================================")
    curr_norm = CurrencyNormalizer()
    for symbol in ["₹", "Rs.", "Rs", "INR"]:
        code = curr_norm.detect_currency(symbol)
        print(f"Currency input '{symbol}' -> '{code}'")

    print("\n==================================================")
    print("STEP 13 — TEST ERROR HANDLING")
    print("==================================================")
    # 1. Unsupported .txt file
    txt_path = Path("test_unsupported.txt")
    txt_path.write_text("random content", encoding="utf-8")
    with open(txt_path, "rb") as f:
        err1 = requests.post(f"{BASE_URL}/api/v1/documents/upload", files={"file": ("test_unsupported.txt", f, "text/plain")})
    print(f"1. Unsupported .txt: Status={err1.status_code}, Response={err1.json()}")
    txt_path.unlink()

    # 2. Empty file (0 bytes)
    empty_path = Path("empty_test.csv")
    empty_path.write_bytes(b"")
    with open(empty_path, "rb") as f:
        err2 = requests.post(f"{BASE_URL}/api/v1/documents/upload", files={"file": ("empty_test.csv", f, "text/csv")})
    print(f"2. Empty 0-byte file: Status={err2.status_code}, Response={err2.json()}")
    empty_path.unlink()

    # 3. Missing document ID on process / empty URL parameter
    err3 = requests.get(f"{BASE_URL}/api/v1/documents/00000000-0000-0000-0000-000000000000")
    print(f"3. Missing document ID: Status={err3.status_code}, Response={err3.json()}")

    # 4. Invalid UUID / non-existent ID
    err4 = requests.get(f"{BASE_URL}/api/v1/documents/non-existent-uuid-123")
    print(f"4. Invalid/Non-existent UUID: Status={err4.status_code}, Response={err4.json()}")

    # 5. Requesting normalized data before processing
    unproc_path = Path("unprocessed.csv")
    unproc_path.write_text("Particulars,2025\nRevenue,1000\n", encoding="utf-8")
    with open(unproc_path, "rb") as f:
        up_unproc = requests.post(f"{BASE_URL}/api/v1/documents/upload", files={"file": ("unprocessed.csv", f, "text/csv")}).json()
    unproc_id = up_unproc["document_id"]
    err5 = requests.get(f"{BASE_URL}/api/v1/documents/{unproc_id}/normalized")
    print(f"5. Normalized before processing: Status={err5.status_code}, Response={err5.json()}")
    unproc_path.unlink()

    # 6. Corrupted PDF
    corrupt_pdf = Path("corrupt.pdf")
    corrupt_pdf.write_bytes(b"%PDF-1.4 garbage binary data that cannot be parsed as valid PDF")
    with open(corrupt_pdf, "rb") as f:
        up_corrupt_pdf = requests.post(f"{BASE_URL}/api/v1/documents/upload", files={"file": ("corrupt.pdf", f, "application/pdf")}).json()
    corrupt_pdf_id = up_corrupt_pdf["document_id"]
    err6 = requests.post(f"{BASE_URL}/api/v1/documents/{corrupt_pdf_id}/process")
    print(f"6. Corrupted PDF processing: Status={err6.status_code}, Response={err6.json()}")
    corrupt_pdf.unlink()

    # 7. Corrupted Excel file
    corrupt_xlsx = Path("corrupt.xlsx")
    corrupt_xlsx.write_bytes(b"PK not a valid zip excel archive")
    with open(corrupt_xlsx, "rb") as f:
        up_corrupt_xlsx = requests.post(f"{BASE_URL}/api/v1/documents/upload", files={"file": ("corrupt.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}).json()
    corrupt_xlsx_id = up_corrupt_xlsx["document_id"]
    err7 = requests.post(f"{BASE_URL}/api/v1/documents/{corrupt_xlsx_id}/process")
    print(f"7. Corrupted Excel processing: Status={err7.status_code}, Response={err7.json()}")
    corrupt_xlsx.unlink()

    # 8. Corrupted CSV file / extraction error
    corrupt_csv = Path("corrupt.csv")
    corrupt_csv.write_bytes(b"\x00\x01\x02\xff\xfe\x00\x00binary")
    with open(corrupt_csv, "rb") as f:
        up_corrupt_csv = requests.post(f"{BASE_URL}/api/v1/documents/upload", files={"file": ("corrupt.csv", f, "text/csv")}).json()
    corrupt_csv_id = up_corrupt_csv["document_id"]
    err8 = requests.post(f"{BASE_URL}/api/v1/documents/{corrupt_csv_id}/process")
    print(f"8. Corrupted/Binary CSV processing: Status={err8.status_code}, Response={err8.json()}")
    corrupt_csv.unlink()

    print("\n==================================================")
    print("STEP 14 — VERIFY DATABASE")
    print("==================================================")
    engine = create_engine(settings.DATABASE_URL)
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"Database dialect: {engine.dialect.name}")
    print(f"Database tables found: {tables}")
    assert "documents" in tables
    assert "financial_data" in tables

    with engine.connect() as conn:
        doc_count = conn.execute(text("SELECT COUNT(*) FROM documents")).scalar()
        fin_count = conn.execute(text("SELECT COUNT(*) FROM financial_data")).scalar()
        print(f"Total documents rows in DB: {doc_count}")
        print(f"Total financial_data rows in DB: {fin_count}")

        # Check foreign key link
        fk_check = conn.execute(text("""
            SELECT d.id, d.filename, d.status, f.revenue, f.assets, f.liabilities, f.equity, f.currency
            FROM documents d
            JOIN financial_data f ON d.id = f.document_id
            WHERE d.id = :doc_id
        """), {"doc_id": csv_doc_id}).mappings().first()
        print(f"Foreign key join verified for doc_id {csv_doc_id}:")
        print(f"  {dict(fk_check)}")

        # Check normalized JSON content persisted in DB
        json_check = conn.execute(text("""
            SELECT normalized_data FROM financial_data WHERE document_id = :doc_id
        """), {"doc_id": csv_doc_id}).scalar()
        if isinstance(json_check, str):
            json_check = json.loads(json_check)
        print(f"Persisted normalized JSON verified. Revenue in JSON: {json_check['financial_data']['revenue']}")

    print("\n==================================================")
    print("STEP 15 — VERIFY SWAGGER")
    print("==================================================")
    r_docs = requests.get(f"{BASE_URL}/docs")
    print(f"GET /docs: Status={r_docs.status_code}")
    assert r_docs.status_code == 200

    r_openapi = requests.get(f"{BASE_URL}/openapi.json")
    print(f"GET /openapi.json: Status={r_openapi.status_code}")
    assert r_openapi.status_code == 200
    paths = list(r_openapi.json()["paths"].keys())
    print(f"Endpoints registered in OpenAPI schema:")
    for p in paths:
        methods = list(r_openapi.json()["paths"][p].keys())
        print(f"  {methods} {p}")

    assert "/api/v1/documents/upload" in paths
    assert "/api/v1/documents/{document_id}/process" in paths
    assert "/api/v1/documents/{document_id}" in paths
    assert "/api/v1/documents/{document_id}/normalized" in paths
    assert "/api/health" in paths
    print("All 5 required endpoints exist in Swagger/OpenAPI!")

if __name__ == "__main__":
    run_all_steps()
