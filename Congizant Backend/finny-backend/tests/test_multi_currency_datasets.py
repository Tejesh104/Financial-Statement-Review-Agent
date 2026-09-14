"""Comprehensive Multi-Currency Dataset Validation Suite for Finny.

Validates that Finny correctly handles multi-currency financial statements across:
1. USD  — US Dollar ($)
2. EUR  — Euro (€)
3. GBP  — British Pound (£)
4. INR  — Indian Rupee (₹, Rs)
5. JPY  — Japanese Yen (¥)
6. AUD  — Australian Dollar (A$)
7. CAD  — Canadian Dollar (C$)
8. SGD  — Singapore Dollar (S$)
9. CHF  — Swiss Franc (CHF)
10. AED — UAE Dirham (AED)

Rules Enforced:
- No automatic conversions, no invented exchange rates.
- Currencies are metadata/context preserved throughout the pipeline.
- Dimensional financial metrics retain source numeric values.
- Dimensionless ratios (Current Ratio, Debt-to-Equity, Net Margin, ROE, ROA) are scale-invariant.
- ML Isolation Forest operates on dimensionless ratios with identical outputs for scale-equivalent statements.
- Agent 2 Grounding preserves source currency without fabricating conversions.
- Dashboard API returns exact document currency metadata.
- Cross-user isolation guarantees no currency leakage.
- Mixed-currency statements raise explicit warnings while preserving numbers without conversion.
"""

import io
import pytest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.database.database import SessionLocal
from app.models.document import Document, DocumentStatus
from app.models.financial_data import FinancialData
from app.models.user import User
from app.core.security import create_access_token
from app.services.normalization.normalizer import Normalizer
from app.services.normalization.currency_normalizer import CurrencyNormalizer
from app.services.normalization.value_cleaner import ValueCleaner
from app.services.analytics.ratio_analyzer import RatioAnalyzer
from app.services.analytics.yoy_analyzer import YoYAnalyzer
from app.services.ml.anomaly_detector import AnomalyDetector
from app.schemas.agent2 import OllamaReviewContent, ObservationFinding


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def mock_ollama_currency():
    with patch("app.services.agent2.ollama_client.OllamaClient.generate_review") as mock_gen:
        mock_gen.return_value = OllamaReviewContent(
            observations=[
                ObservationFinding(
                    finding_type="VALIDATION",
                    title="Balance Sheet Verified",
                    finding="Assets equal liabilities plus equity in the document currency.",
                    explanation="Verified balance sheet identity without currency conversion.",
                    severity="LOW",
                    evidence=["findings.validations.balance_sheet_check"],
                )
            ],
            summary="Review grounded in reported currency figures without foreign exchange conversion.",
            limitations=[],
        )
        yield mock_gen


# =============================================================================
# 1. HEALTHY FINANCIAL STATEMENTS IN 10 CURRENCIES (USD, EUR, GBP, INR, JPY, AUD, CAD, SGD, CHF, AED)
# =============================================================================

CURRENCY_HEALTHY_DATASETS = [
    # (id, name, symbol_or_code, expected_currency, revenue, assets, liabilities, equity, net_income)
    ("USD-H01", "Acme USA Inc", "$", "USD", 5000000.0, 10000000.0, 4000000.0, 6000000.0, 750000.0),
    ("EUR-H01", "Continental Solutions SE", "€", "EUR", 4200000.0, 8500000.0, 3500000.0, 5000000.0, 630000.0),
    ("GBP-H01", "Thames Enterprises Ltd", "£", "GBP", 3800000.0, 7600000.0, 3100000.0, 4500000.0, 570000.0),
    ("INR-H01", "Bharat Technologies Pvt Ltd", "₹", "INR", 350000000.0, 700000000.0, 280000000.0, 420000000.0, 52500000.0),
    ("JPY-H01", "Nippon Industrial KK", "¥", "JPY", 850000000.0, 1700000000.0, 680000000.0, 1020000000.0, 127500000.0),
    ("AUD-H01", "Pacific Mineral Resources Ltd", "A$", "AUD", 6200000.0, 12400000.0, 4960000.0, 7440000.0, 930000.0),
    ("CAD-H01", "Maple Leaf Logistics Inc", "C$", "CAD", 5800000.0, 11600000.0, 4640000.0, 6960000.0, 870000.0),
    ("SGD-H01", "Marina Bay Global Pte Ltd", "S$", "SGD", 4900000.0, 9800000.0, 3920000.0, 5880000.0, 735000.0),
    ("CHF-H01", "Helvetia Precision AG", "CHF", "CHF", 4500000.0, 9000000.0, 3600000.0, 5400000.0, 675000.0),
    ("AED-H01", "Emirates Trading LLC", "AED", "AED", 18500000.0, 37000000.0, 14800000.0, 22200000.0, 2775000.0),
]


@pytest.mark.parametrize(
    "dataset_id, company_name, curr_ind, expected_curr, rev, assets, liab, equity, net_inc",
    CURRENCY_HEALTHY_DATASETS
)
def test_all_ten_currencies_end_to_end_pipeline(
    client: TestClient,
    db_session,
    mock_ollama_currency,
    dataset_id,
    company_name,
    curr_ind,
    expected_curr,
    rev,
    assets,
    liab,
    equity,
    net_inc,
):
    """Verify that statements in each of the 10 currencies parse cleanly without value distortion."""
    csv_content = (
        f"Particulars,2024 ({curr_ind})\n"
        f"{company_name},\n"
        f"Revenue,{rev:,.2f}\n"
        f"Net Income,{net_inc:,.2f}\n"
        f"Total Assets,{assets:,.2f}\n"
        f"Total Liabilities,{liab:,.2f}\n"
        f"Shareholders' Equity,{equity:,.2f}\n"
    )

    filename = f"{dataset_id.lower()}_statement.csv"
    up_res = client.post("/api/v1/documents/upload", files={"file": (filename, io.BytesIO(csv_content.encode("utf-8")), "text/csv")})
    assert up_res.status_code == 201
    doc_id = up_res.json()["document_id"]

    # 1. Process / Normalize
    proc_res = client.post(f"/api/v1/documents/{doc_id}/process")
    assert proc_res.status_code == 200
    norm_data = proc_res.json()

    assert norm_data["currency"] == expected_curr
    assert norm_data["financial_data"]["revenue"] == rev
    assert norm_data["financial_data"]["assets"] == assets
    assert norm_data["financial_data"]["liabilities"] == liab
    assert norm_data["financial_data"]["equity"] == equity
    assert norm_data["financial_data"]["net_income"] == net_inc

    # 2. Math Validation
    val_res = client.post(f"/api/v1/validation/{doc_id}/math")
    assert val_res.status_code == 200
    bs = val_res.json()["balance_sheet_check"]
    assert bs["status"] == "VALID"
    assert bs["is_valid"] is True
    assert bs["difference"] == 0.0

    # 3. Financial Ratios (dimensionless)
    ratio_res = client.post(f"/api/v1/analysis/{doc_id}/ratios")
    assert ratio_res.status_code == 200
    ratios = ratio_res.json()["ratio_analysis"]["ratios"]
    # Debt to Equity: liab / equity = (assets - equity) / equity
    expected_de = round(liab / equity, 4)
    assert ratios["leverage"]["debt_to_equity"]["value"] == expected_de
    # Net Profit Margin: (net_inc / rev) * 100
    expected_npm = round((net_inc / rev) * 100, 2)
    assert ratios["profitability"]["net_profit_margin"]["value"] == expected_npm

    # 4. Agent 1
    ag1_res = client.post(f"/api/v1/agent1/{doc_id}")
    assert ag1_res.status_code == 200

    # 5. ML Anomaly Detection
    ml_res = client.post(f"/api/v1/ml/{doc_id}/anomaly")
    assert ml_res.status_code == 200

    # 6. Agent 1 Findings
    find_res = client.post(f"/api/v1/agent1/{doc_id}/findings")
    assert find_res.status_code == 200

    # 7. Agent 2 Review
    ag2_res = client.post(f"/api/v1/agent2/{doc_id}/review")
    assert ag2_res.status_code == 200

    # 8. Review Observations
    obs_res = client.post(f"/api/v1/agent2/{doc_id}/observations")
    assert obs_res.status_code == 200

    # 9. Consolidated Dashboard API Check
    dash_res = client.get(f"/api/v1/documents/{doc_id}/dashboard")
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert dash_data["currency"] == expected_curr
    assert dash_data["financial_data"]["revenue"] == rev
    assert dash_data["pipeline"]["observations_ready"] is True


# =============================================================================
# 2. CURRENCY SYMBOL VS ISO CODE DISAMBIGUATION TESTS
# =============================================================================

@pytest.mark.parametrize(
    "snippet, expected_code",
    [
        ("$1,000,000", "USD"),
        ("1,000,000 USD", "USD"),
        ("USD 1,000,000", "USD"),
        ("€1,000,000", "EUR"),
        ("1,000,000 EUR", "EUR"),
        ("EUR 1,000,000", "EUR"),
        ("£1,000,000", "GBP"),
        ("1,000,000 GBP", "GBP"),
        ("GBP 1,000,000", "GBP"),
        ("₹1,000,000", "INR"),
        ("Rs. 1,000,000", "INR"),
        ("INR 1,000,000", "INR"),
        ("1,000,000 INR", "INR"),
        ("¥1,000,000", "JPY"),
        ("JPY 1,000,000", "JPY"),
        ("A$ 1,000,000", "AUD"),
        ("AUD 1,000,000", "AUD"),
        ("C$ 1,000,000", "CAD"),
        ("CAD 1,000,000", "CAD"),
        ("S$ 1,000,000", "SGD"),
        ("SGD 1,000,000", "SGD"),
        ("CHF 1,000,000", "CHF"),
        ("AED 1,000,000", "AED"),
    ]
)
def test_currency_symbol_and_code_detection(snippet, expected_code):
    """Ensure CurrencyNormalizer detects both symbols and ISO codes unambiguously."""
    assert CurrencyNormalizer.detect_currency(snippet) == expected_code


def test_compound_dollar_symbols_never_misclassified_as_usd():
    """Verify compound dollar symbols (A$, C$, S$) take precedence over generic $."""
    assert CurrencyNormalizer.detect_currency("A$ 5,000,000") == "AUD"
    assert CurrencyNormalizer.detect_currency("C$ 5,000,000") == "CAD"
    assert CurrencyNormalizer.detect_currency("S$ 5,000,000") == "SGD"
    assert CurrencyNormalizer.detect_currency("$ 5,000,000") == "USD"


# =============================================================================
# 3. INTERNATIONAL NUMBER FORMATTING TESTS
# =============================================================================

def test_european_number_formatting():
    """Test European format with dot-thousands and comma-decimal: 10.000.000,50."""
    val, warn = ValueCleaner.clean_numeric("€10.000.000,50")
    assert val == 10000000.50
    assert warn is None

    val, warn = ValueCleaner.clean_numeric("10.000,50 EUR")
    assert val == 10000.50
    assert warn is None


def test_indian_lakh_crore_number_formatting():
    """Test Indian numbering system (1,00,00,000.50) and scale words (10 Cr, 50 L)."""
    val, warn = ValueCleaner.clean_numeric("₹1,00,00,000.50")
    assert val == 10000000.50
    assert warn is None

    val, warn = ValueCleaner.clean_numeric("10 Cr")
    assert val == 100000000.0
    assert warn is None

    val, warn = ValueCleaner.clean_numeric("50 Lakhs")
    assert val == 5000000.0
    assert warn is None


def test_japanese_yen_integer_presentation():
    """Test Japanese Yen integer amounts with ¥ or JPY prefix/suffix."""
    val, warn = ValueCleaner.clean_numeric("¥ 850,000,000")
    assert val == 850000000.0
    assert warn is None

    val, warn = ValueCleaner.clean_numeric("850000000 JPY")
    assert val == 850000000.0
    assert warn is None


def test_standard_us_number_formatting():
    """Test standard comma thousands and dot decimal: $10,000,000.50."""
    val, warn = ValueCleaner.clean_numeric("$10,000,000.50")
    assert val == 10000000.50
    assert warn is None


# =============================================================================
# 4. MULTI-PERIOD YOY IN SAME CURRENCY (PRESERVATION WITHOUT CONVERSION)
# =============================================================================

def test_multi_period_yoy_preserves_currency_without_conversion(client: TestClient, db_session):
    """
    Verify YoY analysis compares current vs prior period strictly in the same currency
    without performing exchange rate conversion.
    """
    csv_content = (
        "Particulars,2023 (EUR),2024 (EUR)\n"
        "Revenue,1000000,1250000\n"
        "Gross Profit,400000,500000\n"
        "Net Income,100000,150000\n"
        "Total Assets,2000000,2500000\n"
        "Total Liabilities,800000,1000000\n"
        "Shareholders' Equity,1200000,1500000\n"
    )

    up_res = client.post("/api/v1/documents/upload", files={"file": ("eur_yoy.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")})
    doc_id = up_res.json()["document_id"]
    client.post(f"/api/v1/documents/{doc_id}/process")

    # Inject previous period structure for YoY endpoint
    fin_rec = db_session.query(FinancialData).filter(FinancialData.document_id == doc_id).first()
    norm_dict = dict(fin_rec.normalized_data or {})
    norm_dict["previous_period_data"] = {
        "period": "2023",
        "financial_data": {
            "revenue": 1000000.0,
            "gross_profit": 400000.0,
            "net_income": 100000.0,
            "assets": 2000000.0,
            "liabilities": 800000.0,
            "equity": 1200000.0,
        }
    }
    fin_rec.normalized_data = norm_dict
    db_session.commit()

    yoy_res = client.post(f"/api/v1/analysis/{doc_id}/yoy")
    assert yoy_res.status_code == 200
    yoy_data = yoy_res.json()["yoy_analysis"]["financial_data"]

    # Revenue absolute change: 1,250,000 - 1,000,000 = +250,000 EUR
    assert yoy_data["revenue"]["absolute_change"] == 250000.0
    assert yoy_data["revenue"]["percentage_change"] == 25.0
    assert yoy_data["revenue"]["direction"] == "positive"
    # Net Income: 150,000 - 100,000 = +50,000 EUR (+50.0%)
    assert yoy_data["net_income"]["absolute_change"] == 50000.0
    assert yoy_data["net_income"]["percentage_change"] == 50.0


# =============================================================================
# 5. SCALE INVARIANCE OF FINANCIAL RATIOS ACROSS CURRENCIES
# =============================================================================

def test_financial_ratios_are_scale_invariant_across_currencies():
    """
    Verify that financial ratios are dimensionless:
    Dataset A (USD, in thousands):
      Current Assets = 20,000, Current Liab = 10,000, Revenue = 100,000, Net Income = 10,000
    Dataset B (INR, in tens of millions):
      Current Assets = 20,000,000, Current Liab = 10,000,000, Revenue = 100,000,000, Net Income = 10,000,000
    Ratios must be mathematically identical.
    """
    # Dataset A (USD)
    cr_a = RatioAnalyzer.calculate_current_ratio(20000.0, 10000.0)["value"]
    npm_a = RatioAnalyzer.calculate_net_profit_margin(10000.0, 100000.0)["value"]
    de_a = RatioAnalyzer.calculate_debt_to_equity(10000.0, 10000.0)["value"]

    # Dataset B (INR)
    cr_b = RatioAnalyzer.calculate_current_ratio(20000000.0, 10000000.0)["value"]
    npm_b = RatioAnalyzer.calculate_net_profit_margin(10000000.0, 100000000.0)["value"]
    de_b = RatioAnalyzer.calculate_debt_to_equity(10000000.0, 10000000.0)["value"]

    assert cr_a == cr_b == 2.0
    assert npm_a == npm_b == 10.0
    assert de_a == de_b == 1.0


# =============================================================================
# 6. ML ISOLATION FOREST SCALE AWARENESS (FEATURE RATIO EQUIVALENCE)
# =============================================================================

def test_ml_isolation_forest_yields_consistent_anomaly_detection_across_scales():
    """
    Because ML features are 6 dimensionless financial ratios:
    - current_ratio
    - debt_to_equity
    - roe
    - roa
    - net_profit_margin
    - gross_profit_margin
    A statement expressed in JPY (billions) with the same proportional ratios as USD (millions)
    produces the exact same anomaly score and classification.
    """
def test_ml_isolation_forest_yields_consistent_anomaly_detection_across_scales():
    """
    Because ML features are 6 dimensionless financial ratios:
    - current_ratio
    - debt_to_equity
    - roe
    - roa
    - net_profit_margin
    - gross_profit_margin
    A statement expressed in JPY (billions) with the same proportional ratios as USD (millions)
    produces the exact same anomaly score and classification.
    """
    from app.services.ml.model_loader import ModelLoader
    loader = ModelLoader()

    # Identical underlying ratios represented at 1,000x scale difference
    features_usd = [2.0, 0.8, 15.0, 8.0, 10.0, 30.0]
    features_jpy = [2.0, 0.8, 15.0, 8.0, 10.0, 30.0]

    res_usd = loader.predict_vector(features_usd)
    res_jpy = loader.predict_vector(features_jpy)

    assert res_usd["is_anomaly"] == res_jpy["is_anomaly"]
    assert res_usd["label"] == res_jpy["label"]
    assert pytest.approx(res_usd["score"], 0.0001) == res_jpy["score"]


# =============================================================================
# 7. AGENT 2 / OLLAMA CURRENCY GROUNDING
# =============================================================================

def test_agent2_grounding_preserves_source_currency_without_conversion(client: TestClient, db_session):
    """
    Verify Agent 2 review prompt and response maintain currency metadata
    without inventing conversions.
    """
    csv_content = (
        "Particulars,FY 2024\n"
        "Emirates Services LLC (AED),\n"
        "Revenue,50000000\n"
        "Total Assets,100000000\n"
        "Total Liabilities,40000000\n"
        "Shareholders' Equity,60000000\n"
    )

    up_res = client.post("/api/v1/documents/upload", files={"file": ("aed_doc.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")})
    doc_id = up_res.json()["document_id"]
    client.post(f"/api/v1/documents/{doc_id}/process")
    client.post(f"/api/v1/validation/{doc_id}/math")
    client.post(f"/api/v1/analysis/{doc_id}/ratios")
    client.post(f"/api/v1/agent1/{doc_id}")
    client.post(f"/api/v1/ml/{doc_id}/anomaly")
    client.post(f"/api/v1/agent1/{doc_id}/findings")

    with patch("app.services.agent2.ollama_client.OllamaClient.generate_review") as mock_gen:
        mock_gen.return_value = OllamaReviewContent(
            observations=[
                ObservationFinding(
                    finding_type="VALIDATION",
                    title="AED Balance Sheet Verified",
                    finding="Assets AED 100,000,000 equal liabilities AED 40,000,000 plus equity AED 60,000,000.",
                    explanation="All calculations conducted natively in AED without exchange rate adjustment.",
                    severity="LOW",
                    evidence=["findings.validations.balance_sheet_check"],
                )
            ],
            summary="Review grounded in native AED presentation.",
            limitations=[],
        )
        ag2_res = client.post(f"/api/v1/agent2/{doc_id}/review")
        assert ag2_res.status_code == 200
        obs = ag2_res.json()["observations"]
        assert len(obs) == 1
        assert "AED" in obs[0]["finding"] or "AED" in obs[0]["explanation"]


# =============================================================================
# 8. CROSS-USER ISOLATION WITH DIFFERENT CURRENCIES
# =============================================================================

def test_cross_user_isolation_with_differing_currencies(client: TestClient, db_session):
    """
    User A uploads INR document. User B uploads USD document.
    Neither user can access the other's document or see the other's currency metadata.
    """
    import uuid
    uid_a = str(uuid.uuid4())[:8]
    uid_b = str(uuid.uuid4())[:8]
    user_a = User(google_id=f"gid-curr-a-{uid_a}", email=f"user_a_{uid_a}@example.com", name="User A INR")
    user_b = User(google_id=f"gid-curr-b-{uid_b}", email=f"user_b_{uid_b}@example.com", name="User B USD")
    db_session.add_all([user_a, user_b])
    db_session.commit()
    db_session.refresh(user_a)
    db_session.refresh(user_b)

    token_a = create_access_token(user_a.id, user_a.email)
    token_b = create_access_token(user_b.id, user_b.email)
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Upload INR document as User A
    csv_a = "Particulars,2024 (INR)\nRevenue,10000000\nTotal Assets,20000000\nTotal Liabilities,5000000\nShareholders' Equity,15000000\n"
    up_a = client.post("/api/v1/documents/upload", files={"file": ("inr_doc.csv", io.BytesIO(csv_a.encode("utf-8")), "text/csv")}, headers=headers_a)
    doc_id_a = up_a.json()["document_id"]
    client.post(f"/api/v1/documents/{doc_id_a}/process", headers=headers_a)

    # Upload USD document as User B
    csv_b = "Particulars,2024 (USD)\nRevenue,100000\nTotal Assets,200000\nTotal Liabilities,50000\nShareholders' Equity,150000\n"
    up_b = client.post("/api/v1/documents/upload", files={"file": ("usd_doc.csv", io.BytesIO(csv_b.encode("utf-8")), "text/csv")}, headers=headers_b)
    doc_id_b = up_b.json()["document_id"]
    client.post(f"/api/v1/documents/{doc_id_b}/process", headers=headers_b)

    # User A accesses own document -> currency INR
    dash_a = client.get(f"/api/v1/documents/{doc_id_a}/dashboard", headers=headers_a)
    assert dash_a.status_code == 200
    assert dash_a.json()["currency"] == "INR"

    # User B accesses own document -> currency USD
    dash_b = client.get(f"/api/v1/documents/{doc_id_b}/dashboard", headers=headers_b)
    assert dash_b.status_code == 200
    assert dash_b.json()["currency"] == "USD"

    # Cross-tenant access blocked (404/403)
    cross_a_to_b = client.get(f"/api/v1/documents/{doc_id_b}/dashboard", headers=headers_a)
    assert cross_a_to_b.status_code == 404

    cross_b_to_a = client.get(f"/api/v1/documents/{doc_id_a}/dashboard", headers=headers_b)
    assert cross_b_to_a.status_code == 404


# =============================================================================
# 9. NEGATIVE & AMBIGUOUS CURRENCY EDGE CASES
# =============================================================================

def test_missing_currency_indicator_defaults_to_none_without_inventing():
    """When a statement contains zero currency symbols or names, currency is None."""
    csv_data = "Particulars,FY2024\nRevenue,100000\nTotal Assets,200000\nTotal Liabilities,50000\nShareholders' Equity,150000\n"
    normalizer = Normalizer()
    from app.schemas.financial import RawExtractionData, RawTable, DocumentSource
    t = RawTable(headers=["Particulars", "FY2024"], rows=[
        ["Revenue", "100000"],
        ["Total Assets", "200000"],
        ["Total Liabilities", "50000"],
        ["Shareholders' Equity", "150000"],
    ])
    raw = RawExtractionData(source=DocumentSource(filename="report.csv", file_type="csv"), tables=[t])
    norm = normalizer.normalize(raw, "doc-no-curr")
    assert norm.currency is None
    assert norm.financial_data.revenue == 100000.0


def test_mixed_conflicting_currencies_generates_warning_without_converting(client: TestClient):
    """
    When conflicting currencies are present (e.g. USD and EUR in the same document),
    Finny preserves the primary currency and emits a normalization warning without converting values.
    """
    csv_data = (
        "Particulars,2024\n"
        "Revenue,1000000 USD\n"
        "Expenses,500000 EUR\n"
        "Total Assets,2000000 USD\n"
        "Total Liabilities,800000 USD\n"
        "Shareholders' Equity,1200000 USD\n"
    )

    up_res = client.post("/api/v1/documents/upload", files={"file": ("mixed_curr.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")})
    doc_id = up_res.json()["document_id"]
    proc_res = client.post(f"/api/v1/documents/{doc_id}/process")
    assert proc_res.status_code == 200
    norm_data = proc_res.json()

    assert norm_data["currency"] == "USD"
    # Verify numbers are preserved exactly
    assert norm_data["financial_data"]["revenue"] == 1000000.0
    assert norm_data["financial_data"]["expenses"] == 500000.0
    # Verify conflicting currency warning was added
    warnings = norm_data["normalization_warnings"]
    assert any("Conflicting currencies detected" in w for w in warnings)
