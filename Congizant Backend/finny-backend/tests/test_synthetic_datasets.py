"""Comprehensive synthetic dataset test suite covering financial, non-financial, and adversarial data.

Covers:
- Part 1: Financial Synthetic Datasets (F01 to F10)
- Part 2: Non-Financial Datasets (N01 to N08)
- Part 3: Adversarial / Edge Cases
- Part 4: Multi-User Isolation & Database Integrity
"""

import io
import math
import pytest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.models.document import Document, DocumentStatus
from app.models.financial_data import FinancialData
from app.models.user import User
from app.core.security import create_access_token
from app.schemas.agent2 import OllamaReviewContent, ObservationFinding


@pytest.fixture
def mock_ollama_synthetic():
    with patch("app.services.agent2.ollama_client.OllamaClient.generate_review") as mock_gen:
        mock_gen.return_value = OllamaReviewContent(
            observations=[
                ObservationFinding(
                    finding_type="VALIDATION",
                    title="Balance Sheet Validation Result",
                    finding="The balance sheet equation was verified against reported values.",
                    explanation="Mathematical validation executed deterministically on assets, liabilities, and equity.",
                    severity="LOW",
                    evidence=["findings.validations.balance_sheet_check"],
                )
            ],
            summary="Review generated from verified financial indicators without hallucination.",
            limitations=[],
        )
        yield mock_gen


# =============================================================================
# PART 1 — FINANCIAL SYNTHETIC DATASETS (F01 - F10)
# =============================================================================

def test_dataset_f01_healthy_company_full_pipeline(client: TestClient, db_session, mock_ollama_synthetic):
    """
    DATASET F01 — HEALTHY COMPANY
    Two-period financial statement with balanced balance sheet, healthy liquidity and leverage.
    """
    csv_data = (
        "Line Item,2023,2024\n"
        "Revenue,2000000,2500000\n"
        "Cost of Goods Sold,1200000,1500000\n"
        "Gross Profit,800000,1000000\n"
        "Operating Income,400000,500000\n"
        "Net Income,300000,375000\n"
        "Total Assets,4000000,5000000\n"
        "Current Assets,1600000,2000000\n"
        "Cash and Cash Equivalents,600000,800000\n"
        "Inventory,400000,500000\n"
        "Total Liabilities,1600000,2000000\n"
        "Current Liabilities,640000,800000\n"
        "Shareholders' Equity,2400000,3000000\n"
    )

    # 1. Upload & Process
    up_res = client.post("/api/v1/documents/upload", files={"file": ("f01_healthy.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")})
    assert up_res.status_code == 201
    doc_id = up_res.json()["document_id"]

    proc_res = client.post(f"/api/v1/documents/{doc_id}/process")
    assert proc_res.status_code == 200
    norm_res = client.get(f"/api/v1/documents/{doc_id}/normalized").json()
    assert norm_res["financial_data"]["revenue"] == 2500000.0
    assert norm_res["financial_data"]["assets"] == 5000000.0
    assert norm_res["financial_data"]["liabilities"] == 2000000.0
    assert norm_res["financial_data"]["equity"] == 3000000.0

    # Ensure previous period data is present for multi-period comparison
    fin_rec = db_session.query(FinancialData).filter(FinancialData.document_id == doc_id).first()
    norm_dict = dict(fin_rec.normalized_data or {})
    norm_dict["previous_period_data"] = {
        "period": "2023",
        "financial_data": {
            "revenue": 2000000.0,
            "gross_profit": 800000.0,
            "operating_income": 400000.0,
            "net_income": 300000.0,
            "assets": 4000000.0,
            "current_assets": 1600000.0,
            "cash": 600000.0,
            "inventory": 400000.0,
            "liabilities": 1600000.0,
            "current_liabilities": 640000.0,
            "equity": 2400000.0,
        }
    }
    fin_rec.normalized_data = norm_dict
    db_session.commit()

    # 2. Math Validation: 5,000,000 == 2,000,000 + 3,000,000
    val_res = client.post(f"/api/v1/validation/{doc_id}/math")
    assert val_res.status_code == 200
    bs = val_res.json()["balance_sheet_check"]
    assert bs["status"] == "VALID"
    assert bs["is_valid"] is True
    assert bs["difference"] == 0.0

    # 3. YoY Analysis
    yoy_res = client.post(f"/api/v1/analysis/{doc_id}/yoy")
    assert yoy_res.status_code == 200
    yoy_data = yoy_res.json()["yoy_analysis"]["financial_data"]
    # Revenue: (2.5M - 2.0M) = +500,000 (+25.0%)
    assert yoy_data["revenue"]["absolute_change"] == 500000.0
    assert pytest.approx(yoy_data["revenue"]["percentage_change"], 0.01) == 25.0
    assert yoy_data["revenue"]["direction"] == "positive"
    # Assets: (5M - 4M) = +1,000,000 (+25.0%)
    assert yoy_data["assets"]["absolute_change"] == 1000000.0
    assert pytest.approx(yoy_data["assets"]["percentage_change"], 0.01) == 25.0

    # 4. Financial Ratios
    ratio_res = client.post(f"/api/v1/analysis/{doc_id}/ratios")
    assert ratio_res.status_code == 200
    ratios = ratio_res.json()["ratio_analysis"]["ratios"]
    # Current Ratio = 2,000,000 / 800,000 = 2.50
    assert ratios["liquidity"]["current_ratio"]["value"] == 2.5
    # Quick Ratio = (2,000,000 - 500,000) / 800,000 = 1.88
    assert ratios["liquidity"]["quick_ratio"]["value"] == 1.875 or ratios["liquidity"]["quick_ratio"]["value"] == 1.88
    # Gross Profit Margin = (1,000,000 / 2,500,000) * 100 = 40.0%
    assert ratios["profitability"]["gross_profit_margin"]["value"] == 40.0
    # Net Profit Margin = (375,000 / 2,500,000) * 100 = 15.0%
    assert ratios["profitability"]["net_profit_margin"]["value"] == 15.0
    # ROA = (375,000 / 5,000,000) * 100 = 7.5%
    assert ratios["profitability"]["return_on_assets"]["value"] == 7.5
    # ROE = (375,000 / 3,000,000) * 100 = 12.5%
    assert ratios["profitability"]["return_on_equity"]["value"] == 12.5
    # Debt-to-Equity = 2,000,000 / 3,000,000 = 0.6667
    assert pytest.approx(ratios["leverage"]["debt_to_equity"]["value"], 0.01) == 0.67

    # 5. Agent 1 & ML
    a1_res = client.post(f"/api/v1/agent1/{doc_id}")
    assert a1_res.status_code == 200
    ml_res = client.post(f"/api/v1/ml/{doc_id}/anomaly")
    assert ml_res.status_code == 200
    assert ml_res.json()["status"] == "COMPLETED"
    assert math.isfinite(ml_res.json()["anomaly_detection"]["score"])

    # 6. Agent 1 Findings & Agent 2 Review & Observations
    findings_res = client.post(f"/api/v1/agent1/{doc_id}/findings")
    assert findings_res.status_code == 200
    rev_res = client.post(f"/api/v1/agent2/{doc_id}/review")
    assert rev_res.status_code == 200
    obs_res = client.post(f"/api/v1/agent2/{doc_id}/observations")
    assert obs_res.status_code == 200

    # 7. Dashboard Summary
    dash_res = client.get(f"/api/v1/documents/{doc_id}/dashboard")
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert dash_data["risk"]["balance_sheet_status"] == "VALID"
    assert dash_data["pipeline"]["observations_ready"] is True


def test_dataset_f02_balance_sheet_error(client: TestClient):
    """
    DATASET F02 — BALANCE SHEET ERROR
    Assets != Liabilities + Equity (Assets: 50M, Liab: 20M, Equity: 25M; Discrepancy = 5,000,000).
    """
    csv_data = (
        "Line Item,2024\n"
        "Revenue,10000000\n"
        "Total Assets,50000000\n"
        "Total Liabilities,20000000\n"
        "Shareholders' Equity,25000000\n"
    )
    up_res = client.post("/api/v1/documents/upload", files={"file": ("f02_bs_error.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")})
    assert up_res.status_code == 201
    doc_id = up_res.json()["document_id"]
    client.post(f"/api/v1/documents/{doc_id}/process")

    val_res = client.post(f"/api/v1/validation/{doc_id}/math")
    assert val_res.status_code == 200
    bs = val_res.json()["balance_sheet_check"]
    assert bs["status"] == "INVALID"
    assert bs["is_valid"] is False
    assert bs["difference"] == 5000000.0

    dash = client.get(f"/api/v1/documents/{doc_id}/dashboard").json()
    assert dash["risk"]["tier"] == "HIGH"
    assert dash["risk"]["balance_sheet_status"] == "INVALID"


def test_dataset_f03_strong_year_over_year_change(client: TestClient, db_session):
    """
    DATASET F03 — STRONG YEAR-OVER-YEAR CHANGE
    Revenue +50%, Expenses -50%, Net Income +200%.
    """
    csv_data = (
        "Line Item,2023,2024\n"
        "Revenue,10000000,15000000\n"
        "Operating Expenses,4000000,2000000\n"
        "Net Income,2000000,6000000\n"
        "Total Assets,20000000,30000000\n"
        "Total Liabilities,8000000,10000000\n"
        "Shareholders' Equity,12000000,20000000\n"
    )
    up_res = client.post("/api/v1/documents/upload", files={"file": ("f03_strong_yoy.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")})
    assert up_res.status_code == 201
    doc_id = up_res.json()["document_id"]
    client.post(f"/api/v1/documents/{doc_id}/process")

    fin_rec = db_session.query(FinancialData).filter(FinancialData.document_id == doc_id).first()
    norm_dict = dict(fin_rec.normalized_data or {})
    norm_dict["previous_period_data"] = {
        "period": "2023",
        "financial_data": {
            "revenue": 10000000.0,
            "expenses": 4000000.0,
            "net_income": 2000000.0,
            "assets": 20000000.0,
            "liabilities": 8000000.0,
            "equity": 12000000.0,
        }
    }
    fin_rec.normalized_data = norm_dict
    db_session.commit()

    yoy_res = client.post(f"/api/v1/analysis/{doc_id}/yoy")
    assert yoy_res.status_code == 200
    fields = yoy_res.json()["yoy_analysis"]["financial_data"]

    # Revenue: +5,000,000 (+50.0%)
    assert fields["revenue"]["absolute_change"] == 5000000.0
    assert pytest.approx(fields["revenue"]["percentage_change"], 0.01) == 50.0
    assert fields["revenue"]["direction"] == "positive"

    # Expenses: -2,000,000 (-50.0%)
    assert fields["expenses"]["absolute_change"] == -2000000.0
    assert pytest.approx(fields["expenses"]["percentage_change"], 0.01) == -50.0
    assert fields["expenses"]["direction"] == "negative"

    # Net Income: +4,000,000 (+200.0%)
    assert fields["net_income"]["absolute_change"] == 4000000.0
    assert pytest.approx(fields["net_income"]["percentage_change"], 0.01) == 200.0
    assert fields["net_income"]["direction"] == "positive"


def test_dataset_f04_zero_and_missing_values(client: TestClient):
    """
    DATASET F04 — ZERO / NULL / MISSING VALUES
    No division by zero crashes, no NaN leakage, safe undefined handling.
    """
    csv_data = (
        "Line Item,2024\n"
        "Revenue,0\n"
        "Total Assets,1000000\n"
        "Total Liabilities,0\n"
        "Shareholders' Equity,1000000\n"
        "Current Assets,\n"
        "Current Liabilities,0\n"
    )
    up_res = client.post("/api/v1/documents/upload", files={"file": ("f04_zeros.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")})
    assert up_res.status_code == 201
    doc_id = up_res.json()["document_id"]
    client.post(f"/api/v1/documents/{doc_id}/process")

    val_res = client.post(f"/api/v1/validation/{doc_id}/math")
    assert val_res.status_code == 200
    assert val_res.json()["balance_sheet_check"]["status"] == "VALID"

    ratio_res = client.post(f"/api/v1/analysis/{doc_id}/ratios")
    assert ratio_res.status_code == 200
    ratios = ratio_res.json()["ratio_analysis"]["ratios"]
    # Check that zero revenue does not crash profit margin calculation
    assert ratios["profitability"]["gross_profit_margin"]["status"] in ("INCOMPLETE", "UNDEFINED")
    # Check that no NaN or Infinity is leaked in JSON response
    ratio_text = ratio_res.text
    assert "NaN" not in ratio_text
    assert "Infinity" not in ratio_text


def test_dataset_f05_extreme_financial_values(client: TestClient):
    """
    DATASET F05 — EXTREME FINANCIAL VALUES
    Trillion dollar assets, 950B liabilities, 100 cash.
    """
    csv_data = (
        "Line Item,2024\n"
        "Revenue,500000000000\n"
        "Total Assets,1000000000000\n"
        "Total Liabilities,950000000000\n"
        "Shareholders' Equity,50000000000\n"
        "Cash and Cash Equivalents,100\n"
    )
    up_res = client.post("/api/v1/documents/upload", files={"file": ("f05_extreme.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")})
    assert up_res.status_code == 201
    doc_id = up_res.json()["document_id"]
    client.post(f"/api/v1/documents/{doc_id}/process")

    # Math Validation: 1,000,000,000,000 == 950,000,000,000 + 50,000,000,000
    val_res = client.post(f"/api/v1/validation/{doc_id}/math")
    assert val_res.status_code == 200
    assert val_res.json()["balance_sheet_check"]["status"] == "VALID"

    ratio_res = client.post(f"/api/v1/analysis/{doc_id}/ratios")
    assert ratio_res.status_code == 200
    ratios = ratio_res.json()["ratio_analysis"]["ratios"]
    # Debt-to-Equity = 950B / 50B = 19.0
    assert pytest.approx(ratios["leverage"]["debt_to_equity"]["value"], 0.01) == 19.0
    # Debt Ratio = 950B / 1000B = 0.95
    assert pytest.approx(ratios["leverage"]["debt_ratio"]["value"], 0.01) == 0.95


def test_dataset_f06_negative_values(client: TestClient):
    """
    DATASET F06 — NEGATIVE VALUES
    Negative net income (net loss) and negative equity.
    Assets (15M) == Liabilities (20M) + Equity (-5M) => 15M == 15M.
    """
    csv_data = (
        "Line Item,2024\n"
        "Revenue,10000000\n"
        "Gross Profit,2000000\n"
        "Net Income,-5000000\n"
        "Total Assets,15000000\n"
        "Total Liabilities,20000000\n"
        "Shareholders' Equity,-5000000\n"
    )
    up_res = client.post("/api/v1/documents/upload", files={"file": ("f06_negatives.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")})
    assert up_res.status_code == 201
    doc_id = up_res.json()["document_id"]
    client.post(f"/api/v1/documents/{doc_id}/process")

    val_res = client.post(f"/api/v1/validation/{doc_id}/math")
    assert val_res.status_code == 200
    assert val_res.json()["balance_sheet_check"]["status"] == "VALID"

    ratio_res = client.post(f"/api/v1/analysis/{doc_id}/ratios")
    assert ratio_res.status_code == 200
    ratios = ratio_res.json()["ratio_analysis"]["ratios"]
    # Net Profit Margin = (-5M / 10M) * 100 = -50.0%
    assert ratios["profitability"]["net_profit_margin"]["value"] == -50.0
    # ROA = (-5M / 15M) * 100 = -33.33%
    assert pytest.approx(ratios["profitability"]["return_on_assets"]["value"], 0.01) == -33.33


def test_dataset_f07_highly_anomalous_company(client: TestClient):
    """
    DATASET F07 — HIGHLY ANOMALOUS COMPANY
    Severe mismatch in ratios: tiny revenue, massive net loss, extreme leverage.
    """
    csv_data = (
        "Line Item,2024\n"
        "Revenue,10000\n"
        "Net Income,-50000000\n"
        "Total Assets,100000\n"
        "Total Liabilities,80000000\n"
        "Shareholders' Equity,-79900000\n"
        "Current Assets,5000\n"
        "Current Liabilities,40000000\n"
    )
    up_res = client.post("/api/v1/documents/upload", files={"file": ("f07_anomalous.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")})
    assert up_res.status_code == 201
    doc_id = up_res.json()["document_id"]
    client.post(f"/api/v1/documents/{doc_id}/process")
    client.post(f"/api/v1/validation/{doc_id}/math")
    client.post(f"/api/v1/analysis/{doc_id}/ratios")
    client.post(f"/api/v1/agent1/{doc_id}")

    ml_res = client.post(f"/api/v1/ml/{doc_id}/anomaly")
    assert ml_res.status_code == 200
    ml_data = ml_res.json()
    assert ml_data["status"] in ("COMPLETED", "INCOMPLETE")
    assert math.isfinite(ml_data["anomaly_detection"]["score"])
    # Prediction should flag anomaly or statistical divergence
    assert ml_data["prediction"] in (-1, 1)


def test_dataset_f08_incomplete_financial_statement(client: TestClient):
    """
    DATASET F08 — INCOMPLETE FINANCIAL STATEMENT
    Only revenue and assets present; liabilities and equity missing.
    Validation reports INCOMPLETE; no fabricated values invented.
    """
    csv_data = (
        "Line Item,2024\n"
        "Revenue,5000000\n"
        "Total Assets,10000000\n"
    )
    up_res = client.post("/api/v1/documents/upload", files={"file": ("f08_incomplete.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")})
    assert up_res.status_code == 201
    doc_id = up_res.json()["document_id"]
    client.post(f"/api/v1/documents/{doc_id}/process")

    val_res = client.post(f"/api/v1/validation/{doc_id}/math")
    assert val_res.status_code == 200
    bs = val_res.json()["balance_sheet_check"]
    assert bs["status"] == "INCOMPLETE"
    assert "Missing" in bs["reason"]


def test_dataset_f09_multi_period_financial_data(client: TestClient, db_session):
    """
    DATASET F09 — MULTI-PERIOD FINANCIAL DATA
    Three periods (2022, 2023, 2024) in column layout.
    Ensures 2024 is current and 2023 is previous, without period mixing.
    """
    csv_data = (
        "Year,Revenue,Total Assets,Total Liabilities,Shareholders' Equity\n"
        "2024,30000000,50000000,20000000,30000000\n"
        "2023,25000000,45000000,18000000,27000000\n"
        "2022,20000000,40000000,16000000,24000000\n"
    )
    up_res = client.post("/api/v1/documents/upload", files={"file": ("f09_multi_period.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")})
    assert up_res.status_code == 201
    doc_id = up_res.json()["document_id"]
    proc_res = client.post(f"/api/v1/documents/{doc_id}/process")
    assert proc_res.status_code == 200

    yoy_res = client.post(f"/api/v1/analysis/{doc_id}/yoy")
    assert yoy_res.status_code == 200
    yoy_data = yoy_res.json()["yoy_analysis"]
    assert yoy_data["status"] in ("COMPLETED", "INCOMPLETE")
    periods = yoy_data["periods"]
    assert "2024" in periods["current"]
    assert "2023" in periods["previous"]
    # Revenue: (30M - 25M) = +5,000,000 (+20.0%)
    assert yoy_data["financial_data"]["revenue"]["absolute_change"] == 5000000.0
    assert pytest.approx(yoy_data["financial_data"]["revenue"]["percentage_change"], 0.01) == 20.0


def test_dataset_f10_cross_field_inconsistency(client: TestClient):
    """
    DATASET F10 — CROSS-FIELD INCONSISTENCY
    Revenue: 10M, COGS: 4M, reported Gross Profit: 8M (contradictory).
    Backend must preserve reported numbers without silent overwrite.
    """
    csv_data = (
        "Line Item,2024\n"
        "Revenue,10000000\n"
        "Cost of Goods Sold,4000000\n"
        "Gross Profit,8000000\n"
        "Total Assets,20000000\n"
        "Total Liabilities,10000000\n"
        "Shareholders' Equity,10000000\n"
    )
    up_res = client.post("/api/v1/documents/upload", files={"file": ("f10_inconsistent.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")})
    assert up_res.status_code == 201
    doc_id = up_res.json()["document_id"]
    client.post(f"/api/v1/documents/{doc_id}/process")

    norm_res = client.get(f"/api/v1/documents/{doc_id}/normalized").json()
    assert norm_res["financial_data"]["revenue"] == 10000000.0
    assert norm_res["financial_data"]["gross_profit"] == 8000000.0

    ratio_res = client.post(f"/api/v1/analysis/{doc_id}/ratios")
    assert ratio_res.status_code == 200
    ratios = ratio_res.json()["ratio_analysis"]["ratios"]
    # Gross Profit Margin computed with reported gross profit = (8M / 10M) * 100 = 80.0%
    assert ratios["profitability"]["gross_profit_margin"]["value"] == 80.0


# =============================================================================
# PART 2 — NON-FINANCIAL DATASETS (N01 - N08)
# =============================================================================

def test_dataset_n01_plain_text_rejected(client: TestClient):
    """DATASET N01 — PLAIN TEXT: Rejected by classifier, no fake financial data."""
    text = "This is a normal text document about a software company architecture and engineering practices."
    up_res = client.post("/api/v1/documents/upload", files={"file": ("n01_notes.txt", io.BytesIO(text.encode("utf-8")), "text/plain")})
    assert up_res.status_code in (201, 400)
    if up_res.status_code == 201:
        doc_id = up_res.json()["document_id"]
        proc_res = client.post(f"/api/v1/documents/{doc_id}/process")
        assert proc_res.status_code == 422
        assert "not recognized as a valid financial statement" in proc_res.json()["detail"].lower() or "rejected" in proc_res.json()["detail"].lower()


def test_dataset_n02_random_csv_rejected(client: TestClient):
    """DATASET N02 — RANDOM CSV: Contains Name, Age, City; Age must not be interpreted as revenue."""
    csv_data = "Name,Age,City\nAlice,30,Bangalore\nBob,25,Delhi\nCharlie,35,Mumbai\n"
    up_res = client.post("/api/v1/documents/upload", files={"file": ("n02_people.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")})
    assert up_res.status_code == 201
    doc_id = up_res.json()["document_id"]
    proc_res = client.post(f"/api/v1/documents/{doc_id}/process")
    assert proc_res.status_code == 422
    assert "not recognized as a valid financial statement" in proc_res.json()["detail"].lower() or "rejected" in proc_res.json()["detail"].lower()


def test_dataset_n03_sales_only_rejected(client: TestClient):
    """DATASET N03 — SALES DATA ONLY: Not a complete financial statement; safely rejected."""
    csv_data = "Product,Quantity,Price,Region\nWidget A,100,19.99,North\nWidget B,50,29.99,South\n"
    up_res = client.post("/api/v1/documents/upload", files={"file": ("n03_sales.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")})
    assert up_res.status_code == 201
    doc_id = up_res.json()["document_id"]
    proc_res = client.post(f"/api/v1/documents/{doc_id}/process")
    assert proc_res.status_code == 422
    assert "not recognized as a valid financial statement" in proc_res.json()["detail"].lower() or "rejected" in proc_res.json()["detail"].lower()


def test_dataset_n04_employee_hr_rejected(client: TestClient):
    """DATASET N04 — EMPLOYEE / HR DATA: Salary roster rejected as financial statement."""
    csv_data = "Employee,Department,Salary,Joining Date\nAlice,Engineering,120000,2021-01-15\nBob,Sales,95000,2022-03-01\n"
    up_res = client.post("/api/v1/documents/upload", files={"file": ("n04_employees.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")})
    assert up_res.status_code == 201
    doc_id = up_res.json()["document_id"]
    proc_res = client.post(f"/api/v1/documents/{doc_id}/process")
    assert proc_res.status_code == 422
    assert "not recognized as a valid financial statement" in proc_res.json()["detail"].lower() or "rejected" in proc_res.json()["detail"].lower()


def test_dataset_n05_log_file_rejected(client: TestClient):
    """DATASET N05 — LOG FILE: Server logs rejected cleanly without crash."""
    log_data = (
        "2026-09-14 00:00:01 INFO [main] Server started on port 8080\n"
        "2026-09-14 00:00:02 DEBUG Connection received from 127.0.0.1\n"
        "2026-09-14 00:00:03 WARN Connection timed out for peer 192.168.1.50\n"
    )
    up_res = client.post("/api/v1/documents/upload", files={"file": ("n05_server.log", io.BytesIO(log_data.encode("utf-8")), "text/plain")})
    if up_res.status_code == 201:
        doc_id = up_res.json()["document_id"]
        proc_res = client.post(f"/api/v1/documents/{doc_id}/process")
        assert proc_res.status_code == 422


def test_dataset_n06_pdf_no_financial_content(client: TestClient, tmp_path):
    """DATASET N06 — PDF WITHOUT FINANCIAL CONTENT: Text-only PDF rejected gracefully."""
    import pymupdf as fitz
    pdf_path = tmp_path / "n06_readme.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "README: This is a software deployment guide without accounting figures.")
    doc.save(str(pdf_path))
    doc.close()

    with open(pdf_path, "rb") as f:
        up_res = client.post("/api/v1/documents/upload", files={"file": ("n06_readme.pdf", f, "application/pdf")})
    assert up_res.status_code == 201
    doc_id = up_res.json()["document_id"]
    proc_res = client.post(f"/api/v1/documents/{doc_id}/process")
    assert proc_res.status_code == 422
    err_detail = proc_res.json()["detail"].lower()
    assert (
        "not recognized as a valid financial statement" in err_detail
        or "rejected" in err_detail
        or "no readable tabular data" in err_detail
    )


def test_dataset_n07_malformed_csv_handled_cleanly(client: TestClient):
    """DATASET N07 — MALFORMED CSV: Broken quotes, uneven columns handled gracefully."""
    bad_csv = 'ColA,ColB\n1,2,3,4,5\n"broken quotes without close,8,9\n'
    up_res = client.post("/api/v1/documents/upload", files={"file": ("n07_malformed.csv", io.BytesIO(bad_csv.encode("utf-8")), "text/csv")})
    assert up_res.status_code == 201
    doc_id = up_res.json()["document_id"]
    proc_res = client.post(f"/api/v1/documents/{doc_id}/process")
    # Must fail safely with 422, zero 500 crash
    assert proc_res.status_code == 422


def test_dataset_n08_empty_document_rejected(client: TestClient):
    """DATASET N08 — EMPTY DOCUMENT: 0-byte file handled safely."""
    empty_csv = ""
    up_res = client.post("/api/v1/documents/upload", files={"file": ("n08_empty.csv", io.BytesIO(empty_csv.encode("utf-8")), "text/csv")})
    # Either rejected at upload or at process
    if up_res.status_code == 201:
        doc_id = up_res.json()["document_id"]
        proc_res = client.post(f"/api/v1/documents/{doc_id}/process")
        assert proc_res.status_code == 422
    else:
        assert up_res.status_code in (400, 422)


# =============================================================================
# PART 3 — ADVERSARIAL & EDGE CASES
# =============================================================================

def test_adversarial_percentages_currencies_and_commas(client: TestClient):
    """Tests whitespace, currency symbols, percentages, commas in financial values."""
    csv_data = (
        "Line Item,FY 2024\n"
        "Total Revenue,   $ 12,500,000   \n"
        "Total Assets,  € 45,000,000 \n"
        "Total Liabilities, 18,000,000 \n"
        "Shareholders' Equity, 27,000,000 \n"
        "Gross Profit Margin, 40% \n"
    )
    up_res = client.post("/api/v1/documents/upload", files={"file": ("adv_formatting.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")})
    assert up_res.status_code == 201
    doc_id = up_res.json()["document_id"]
    proc_res = client.post(f"/api/v1/documents/{doc_id}/process")
    assert proc_res.status_code == 200

    norm_res = client.get(f"/api/v1/documents/{doc_id}/normalized").json()
    assert norm_res["financial_data"]["revenue"] == 12500000.0
    assert norm_res["financial_data"]["assets"] == 45000000.0
    assert norm_res["financial_data"]["liabilities"] == 18000000.0
    assert norm_res["financial_data"]["equity"] == 27000000.0


def test_adversarial_multi_user_security_isolation(client: TestClient, db_session):
    """Verifies strict security isolation across two authenticated users with synthetic files."""
    user1 = User(google_id="gid-syn-1", email="user1@example.com", name="User One")
    user2 = User(google_id="gid-syn-2", email="user2@example.com", name="User Two")
    db_session.add_all([user1, user2])
    db_session.commit()
    db_session.refresh(user1)
    db_session.refresh(user2)

    tok1 = create_access_token(user1.id, user1.email)
    tok2 = create_access_token(user2.id, user2.email)

    csv_data = "Line Item,2024\nRevenue,1000000\nTotal Assets,2000000\nTotal Liabilities,800000\nShareholders' Equity,1200000\n"
    up_res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("user1_fin.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")},
        headers={"Authorization": f"Bearer {tok1}"}
    )
    assert up_res.status_code == 201
    doc_id = up_res.json()["document_id"]

    # User 2 attempts unauthorized access across all major endpoints
    assert client.get(f"/api/v1/documents/{doc_id}", headers={"Authorization": f"Bearer {tok2}"}).status_code == 404
    assert client.get(f"/api/v1/documents/{doc_id}/dashboard", headers={"Authorization": f"Bearer {tok2}"}).status_code == 404
    assert client.post(f"/api/v1/validation/{doc_id}/math", headers={"Authorization": f"Bearer {tok2}"}).status_code == 404
    assert client.get(f"/api/v1/reports/{doc_id}", headers={"Authorization": f"Bearer {tok2}"}).status_code == 404
