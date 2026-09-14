import uuid
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.analytics.ratio_analyzer import RatioAnalyzer
from app.models.document import Document, DocumentStatus
from app.models.financial_data import FinancialData


# ==============================================================================
# UNIT TESTS: RatioAnalyzer
# ==============================================================================

def test_unit_current_ratio():
    """TEST 1: Current Ratio = Current Assets (200) / Current Liabilities (100) = 2.0"""
    res = RatioAnalyzer.calculate_current_ratio(current_assets=200.0, current_liabilities=100.0)
    assert res["status"] == "COMPLETED"
    assert res["value"] == 2.0
    assert res["reason"] is None


def test_unit_quick_ratio():
    """TEST 2: Quick Ratio = (Current Assets (200) - Inventory (50)) / Current Liabilities (100) = 1.5"""
    res = RatioAnalyzer.calculate_quick_ratio(current_assets=200.0, inventory=50.0, current_liabilities=100.0)
    assert res["status"] == "COMPLETED"
    assert res["value"] == 1.5
    assert res["reason"] is None


def test_unit_gross_profit_margin():
    """TEST 3: Gross Profit Margin = (Gross Profit (400) / Revenue (1000)) * 100 = 40.0%"""
    res = RatioAnalyzer.calculate_gross_profit_margin(gross_profit=400.0, revenue=1000.0)
    assert res["status"] == "COMPLETED"
    assert res["value"] == 40.0
    assert res["reason"] is None


def test_unit_net_profit_margin():
    """TEST 4: Net Profit Margin = (Net Profit (100) / Revenue (1000)) * 100 = 10.0%"""
    res = RatioAnalyzer.calculate_net_profit_margin(net_profit=100.0, revenue=1000.0)
    assert res["status"] == "COMPLETED"
    assert res["value"] == 10.0
    assert res["reason"] is None


def test_unit_return_on_assets():
    """TEST 5: ROA = (Net Profit (100) / Assets (2000)) * 100 = 5.0%"""
    res = RatioAnalyzer.calculate_return_on_assets(net_profit=100.0, assets=2000.0)
    assert res["status"] == "COMPLETED"
    assert res["value"] == 5.0
    assert res["reason"] is None


def test_unit_return_on_equity():
    """TEST 6: ROE = (Net Profit (100) / Equity (500)) * 100 = 20.0%"""
    res = RatioAnalyzer.calculate_return_on_equity(net_profit=100.0, equity=500.0)
    assert res["status"] == "COMPLETED"
    assert res["value"] == 20.0
    assert res["reason"] is None


def test_unit_debt_to_equity():
    """TEST 7: Debt-to-Equity = Debt (300) / Equity (600) = 0.5"""
    res = RatioAnalyzer.calculate_debt_to_equity(debt=300.0, equity=600.0)
    assert res["status"] == "COMPLETED"
    assert res["value"] == 0.5
    assert res["reason"] is None


def test_unit_debt_ratio():
    """TEST 8: Debt Ratio = Debt (300) / Assets (1000) = 0.3"""
    res = RatioAnalyzer.calculate_debt_ratio(debt=300.0, assets=1000.0)
    assert res["status"] == "COMPLETED"
    assert res["value"] == 0.3
    assert res["reason"] is None


def test_unit_missing_current_liabilities():
    """TEST 9: Missing Current Liabilities -> Current Ratio = null, status = INCOMPLETE"""
    res = RatioAnalyzer.calculate_current_ratio(current_assets=200.0, current_liabilities=None)
    assert res["status"] == "INCOMPLETE"
    assert res["value"] is None
    assert "current liabilities" in res["reason"].lower()


def test_unit_missing_revenue():
    """TEST 10: Missing Revenue -> Gross Profit Margin and Net Profit Margin = null, status = INCOMPLETE"""
    gpm = RatioAnalyzer.calculate_gross_profit_margin(gross_profit=400.0, revenue=None)
    assert gpm["status"] == "INCOMPLETE"
    assert gpm["value"] is None
    assert "revenue" in gpm["reason"].lower()

    npm = RatioAnalyzer.calculate_net_profit_margin(net_profit=100.0, revenue=None)
    assert npm["status"] == "INCOMPLETE"
    assert npm["value"] is None
    assert "revenue" in npm["reason"].lower()


def test_unit_missing_equity():
    """TEST 11: Missing Equity -> ROE and Debt-to-Equity = null, status = INCOMPLETE"""
    roe = RatioAnalyzer.calculate_return_on_equity(net_profit=100.0, equity=None)
    assert roe["status"] == "INCOMPLETE"
    assert roe["value"] is None
    assert "equity" in roe["reason"].lower()

    dte = RatioAnalyzer.calculate_debt_to_equity(debt=300.0, equity=None)
    assert dte["status"] == "INCOMPLETE"
    assert dte["value"] is None
    assert "equity" in dte["reason"].lower()


def test_unit_zero_revenue():
    """TEST 12: Zero Revenue -> value = null, status = UNDEFINED, no crash"""
    gpm = RatioAnalyzer.calculate_gross_profit_margin(gross_profit=400.0, revenue=0.0)
    assert gpm["status"] == "UNDEFINED"
    assert gpm["value"] is None
    assert "zero" in gpm["reason"].lower()

    npm = RatioAnalyzer.calculate_net_profit_margin(net_profit=100.0, revenue=0.0)
    assert npm["status"] == "UNDEFINED"
    assert npm["value"] is None
    assert "zero" in npm["reason"].lower()


def test_unit_zero_assets():
    """TEST 13: Zero Assets -> ROA and Debt Ratio = null, status = UNDEFINED, no crash"""
    roa = RatioAnalyzer.calculate_return_on_assets(net_profit=100.0, assets=0.0)
    assert roa["status"] == "UNDEFINED"
    assert roa["value"] is None
    assert "zero" in roa["reason"].lower()

    dr = RatioAnalyzer.calculate_debt_ratio(debt=300.0, assets=0.0)
    assert dr["status"] == "UNDEFINED"
    assert dr["value"] is None
    assert "zero" in dr["reason"].lower()


def test_unit_zero_equity():
    """TEST 14: Zero Equity -> ROE and Debt-to-Equity = null, status = UNDEFINED, no crash"""
    roe = RatioAnalyzer.calculate_return_on_equity(net_profit=100.0, equity=0.0)
    assert roe["status"] == "UNDEFINED"
    assert roe["value"] is None
    assert "zero" in roe["reason"].lower()

    dte = RatioAnalyzer.calculate_debt_to_equity(debt=300.0, equity=0.0)
    assert dte["status"] == "UNDEFINED"
    assert dte["value"] is None
    assert "zero" in dte["reason"].lower()


def test_unit_negative_net_profit():
    """TEST 15: Negative Net Profit (-100 / 1000 * 100 = -10%) calculates normally without rejection"""
    npm = RatioAnalyzer.calculate_net_profit_margin(net_profit=-100.0, revenue=1000.0)
    assert npm["status"] == "COMPLETED"
    assert npm["value"] == -10.0
    assert npm["reason"] is None


def test_unit_zero_debt():
    """TEST 16: Zero Debt (0 / 500 = 0.0) treats 0 as valid numerator, not missing"""
    dte = RatioAnalyzer.calculate_debt_to_equity(debt=0.0, equity=500.0)
    assert dte["status"] == "COMPLETED"
    assert dte["value"] == 0.0

    dr = RatioAnalyzer.calculate_debt_ratio(debt=0.0, assets=1000.0)
    assert dr["status"] == "COMPLETED"
    assert dr["value"] == 0.0


def test_unit_large_values():
    """TEST 17: Large values in trillions maintain numerical precision"""
    net_profit = 250_000_000_000.0
    equity = 1_000_000_000_000.0
    roe = RatioAnalyzer.calculate_return_on_equity(net_profit=net_profit, equity=equity)
    assert roe["status"] == "COMPLETED"
    assert roe["value"] == 25.0


def test_unit_multiple_ratios():
    """TEST 18: Provide complete normalized dataset and verify all applicable ratios compute"""
    metrics = {
        "current_assets": 200.0,
        "current_liabilities": 100.0,
        "inventory": 50.0,
        "revenue": 1000.0,
        "gross_profit": 400.0,
        "net_profit": 100.0,
        "assets": 2000.0,
        "equity": 500.0,
        "debt": 300.0,
    }
    res = RatioAnalyzer.analyze_ratios(metrics)
    assert res["status"] == "COMPLETED"
    r = res["ratios"]
    assert r["liquidity"]["current_ratio"]["value"] == 2.0
    assert r["liquidity"]["quick_ratio"]["value"] == 1.5
    assert r["profitability"]["gross_profit_margin"]["value"] == 40.0
    assert r["profitability"]["net_profit_margin"]["value"] == 10.0
    assert r["profitability"]["return_on_assets"]["value"] == 5.0
    assert r["profitability"]["return_on_equity"]["value"] == 20.0
    assert r["leverage"]["debt_to_equity"]["value"] == 0.6
    assert r["leverage"]["debt_ratio"]["value"] == 0.15


def test_unit_missing_inventory():
    """TEST 19: Missing inventory -> Current ratio calculates, Quick ratio is INCOMPLETE"""
    metrics = {
        "current_assets": 200.0,
        "current_liabilities": 100.0,
        "inventory": None,
    }
    res = RatioAnalyzer.analyze_ratios(metrics)
    r = res["ratios"]
    assert r["liquidity"]["current_ratio"]["status"] == "COMPLETED"
    assert r["liquidity"]["current_ratio"]["value"] == 2.0
    assert r["liquidity"]["quick_ratio"]["status"] == "INCOMPLETE"
    assert r["liquidity"]["quick_ratio"]["value"] is None


def test_unit_partial_dataset():
    """TEST 20: Partial dataset computes available ratios and flags unavailable without fabricating data"""
    metrics = {
        "revenue": 1000.0,
        "gross_profit": 400.0,
        "assets": 2000.0,
    }
    res = RatioAnalyzer.analyze_ratios(metrics)
    r = res["ratios"]
    assert r["profitability"]["gross_profit_margin"]["status"] == "COMPLETED"
    assert r["profitability"]["gross_profit_margin"]["value"] == 40.0
    assert r["liquidity"]["current_ratio"]["status"] == "INCOMPLETE"
    assert r["profitability"]["net_profit_margin"]["status"] == "INCOMPLETE"


# ==============================================================================
# INTEGRATION TESTS: API POST /api/v1/analysis/{document_id}/ratios
# ==============================================================================

def test_api_valid_document_complete_ratios(client: TestClient, db_session: Session):
    """API TEST 1 & 2: Valid normalized document with complete metrics -> 200 and all ratios computed"""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="complete_report.csv",
        file_type="csv",
        file_path=str(Path("uploads") / "complete_report.csv"),
        status=DocumentStatus.NORMALIZED.value
    )
    fin_record = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        company_name="Apex Global Ltd",
        currency="INR",
        fiscal_year="2024-25",
        revenue=10000000.0,
        assets=20000000.0,
        liabilities=8000000.0,
        equity=12000000.0,
        normalized_data={
            "document_id": doc_id,
            "company": {"name": "Apex Global Ltd"},
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
    db_session.add(doc)
    db_session.add(fin_record)
    db_session.commit()

    response = client.post(f"/api/v1/analysis/{doc_id}/ratios")
    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == doc_id
    ratios = data["ratio_analysis"]["ratios"]
    assert ratios["liquidity"]["current_ratio"]["value"] == 2.0
    assert ratios["liquidity"]["quick_ratio"]["value"] == 1.5
    assert ratios["profitability"]["gross_profit_margin"]["value"] == 40.0
    assert ratios["profitability"]["net_profit_margin"]["value"] == 15.0
    assert ratios["profitability"]["return_on_assets"]["value"] == 7.5
    assert ratios["profitability"]["return_on_equity"]["value"] == 12.5
    assert ratios["leverage"]["debt_to_equity"]["value"] == 0.6667
    assert ratios["leverage"]["debt_ratio"]["value"] == 0.4


def test_api_missing_fields(client: TestClient, db_session: Session):
    """API TEST 3: Normalized document missing some fields returns 200 with INCOMPLETE individual statuses"""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="partial_fields.csv",
        file_type="csv",
        file_path=str(Path("uploads") / "partial_fields.csv"),
        status=DocumentStatus.NORMALIZED.value
    )
    fin_record = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        company_name="Partial Ltd",
        currency="USD",
        revenue=5000000.0,
        assets=10000000.0,
        liabilities=4000000.0,
        equity=6000000.0,
        normalized_data={
            "document_id": doc_id,
            "company": {"name": "Partial Ltd"},
            "financial_data": {
                "revenue": 5000000.0,
                "assets": 10000000.0,
                "equity": 6000000.0,
                "liabilities": 4000000.0,
            }
        }
    )
    db_session.add(doc)
    db_session.add(fin_record)
    db_session.commit()

    response = client.post(f"/api/v1/analysis/{doc_id}/ratios")
    assert response.status_code == 200
    data = response.json()
    r = data["ratio_analysis"]["ratios"]
    assert r["liquidity"]["current_ratio"]["status"] == "INCOMPLETE"
    assert r["liquidity"]["quick_ratio"]["status"] == "INCOMPLETE"
    assert r["leverage"]["debt_to_equity"]["status"] == "COMPLETED"
    assert r["leverage"]["debt_ratio"]["status"] == "COMPLETED"


def test_api_zero_denominator(client: TestClient, db_session: Session):
    """API TEST 4: Zero denominator returns 200 with UNDEFINED status and value null"""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="zero_rev.csv",
        file_type="csv",
        file_path=str(Path("uploads") / "zero_rev.csv"),
        status=DocumentStatus.NORMALIZED.value
    )
    fin_record = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        company_name="Zero Rev Corp",
        currency="USD",
        revenue=0.0,
        assets=10000000.0,
        liabilities=4000000.0,
        equity=6000000.0,
        normalized_data={
            "document_id": doc_id,
            "financial_data": {
                "revenue": 0.0,
                "gross_profit": 500000.0,
                "net_profit": 100000.0,
                "assets": 10000000.0,
                "equity": 6000000.0,
            }
        }
    )
    db_session.add(doc)
    db_session.add(fin_record)
    db_session.commit()

    response = client.post(f"/api/v1/analysis/{doc_id}/ratios")
    assert response.status_code == 200
    data = response.json()
    prof = data["ratio_analysis"]["ratios"]["profitability"]
    assert prof["gross_profit_margin"]["status"] == "UNDEFINED"
    assert prof["gross_profit_margin"]["value"] is None
    assert "zero" in prof["gross_profit_margin"]["reason"].lower()


def test_api_nonexistent_document(client: TestClient):
    """API TEST 5: Nonexistent document returns 404"""
    nonexistent_id = str(uuid.uuid4())
    response = client.post(f"/api/v1/analysis/{nonexistent_id}/ratios")
    assert response.status_code == 404
    assert f"Document with ID '{nonexistent_id}' not found." in response.json()["detail"]


def test_api_unnormalized_document(client: TestClient, db_session: Session):
    """API TEST 6: Unnormalized document returns 400"""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="pending.pdf",
        file_type="pdf",
        file_path="uploads/pending.pdf",
        status=DocumentStatus.UPLOADED.value
    )
    db_session.add(doc)
    db_session.commit()

    response = client.post(f"/api/v1/analysis/{doc_id}/ratios")
    assert response.status_code == 400
    assert "has not been normalized yet" in response.json()["detail"]


def test_api_db_persistence(client: TestClient, db_session: Session):
    """API TEST 8: Verify ratio result is persisted in financial_data.normalized_data['analysis']['ratios']"""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="persist_test.csv",
        file_type="csv",
        file_path="uploads/persist_test.csv",
        status=DocumentStatus.NORMALIZED.value
    )
    fin_record = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        company_name="Persist Corp",
        currency="USD",
        revenue=1000.0,
        assets=2000.0,
        equity=500.0,
        normalized_data={
            "document_id": doc_id,
            "financial_data": {
                "revenue": 1000.0,
                "gross_profit": 400.0,
                "net_profit": 100.0,
                "assets": 2000.0,
                "equity": 500.0,
            }
        }
    )
    db_session.add(doc)
    db_session.add(fin_record)
    db_session.commit()

    response = client.post(f"/api/v1/analysis/{doc_id}/ratios")
    assert response.status_code == 200

    # Refresh record from database
    db_session.refresh(fin_record)
    stored_norm = fin_record.normalized_data or {}
    assert "analysis" in stored_norm
    assert "ratios" in stored_norm["analysis"]
    persisted_ratios = stored_norm["analysis"]["ratios"]
    assert persisted_ratios["ratios"]["profitability"]["gross_profit_margin"]["value"] == 40.0
