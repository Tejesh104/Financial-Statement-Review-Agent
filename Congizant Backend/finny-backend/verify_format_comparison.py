import requests
import json

base = "http://127.0.0.1:8000"

def test_format(filename, mime):
    with open(filename, "rb") as f:
        doc_id = requests.post(
            f"{base}/api/v1/documents/upload",
            files={"file": (filename, f, mime)}
        ).json()["document_id"]
    requests.post(f"{base}/api/v1/documents/{doc_id}/process")
    return requests.get(f"{base}/api/v1/documents/{doc_id}/normalized").json()

csv_res = test_format("sample_financial.csv", "text/csv")
excel_res = test_format("sample_financial.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
pdf_res = test_format("sample_financial.pdf", "application/pdf")

expected = {
    "revenue": 12500000.0,
    "assets": 45000000.0,
    "liabilities": 18000000.0,
    "equity": 27000000.0
}

print("\n=================== FORMAT COMPARISON ===================")
print(f"{'Field':<20} | {'CSV':<15} | {'Excel':<15} | {'PDF':<15} | {'Match?':<6}")
print("-" * 80)
for k, exp_val in expected.items():
    c = csv_res["financial_data"][k]
    e = excel_res["financial_data"][k]
    p = pdf_res["financial_data"][k]
    m = (c == e == p == exp_val)
    print(f"{k:<20} | {c:<15} | {e:<15} | {p:<15} | {str(m):<6}")

c_cur = csv_res.get("currency")
e_cur = excel_res.get("currency")
p_cur = pdf_res.get("currency")
print(f"{'currency':<20} | {str(c_cur):<15} | {str(e_cur):<15} | {str(p_cur):<15} | {str(c_cur == e_cur == p_cur == 'INR'):<6}")

c_fy = csv_res.get("period", {}).get("fiscal_year")
e_fy = excel_res.get("period", {}).get("fiscal_year")
p_fy = pdf_res.get("period", {}).get("fiscal_year")
print(f"{'fiscal_year':<20} | {str(c_fy):<15} | {str(e_fy):<15} | {str(p_fy):<15} | {str(c_fy == e_fy == p_fy == '2024-25'):<6}")

c_name = csv_res.get("company", {}).get("name")
e_name = excel_res.get("company", {}).get("name")
p_name = pdf_res.get("company", {}).get("name")
print(f"{'company.name':<20} | {str(c_name):<15} | {str(e_name):<15} | {str(p_name):<15} | {str(c_name == e_name == p_name == 'ABC Limited'):<6}")
print("=========================================================\n")
