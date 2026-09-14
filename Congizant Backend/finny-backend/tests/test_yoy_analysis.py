import uuid
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.analytics.yoy_analyzer import YoYAnalyzer
from app.models.document import Document, DocumentStatus
from app.models.financial_data import FinancialData


# ==============================================================================
# UNIT TESTS: YoYAnalyzer
# ==============================================================================

def test_unit_normal_growth():
    """TEST 1: Normal growth (Prev: 10M, Curr: 12.5M -> +2.5M, +25%, positive)."""
    res = YoYAnalyzer.calculate_field_yoy(previous=10_000_000.0, current=12_500_000.0)
    assert res["status"] == "COMPLETED"
    assert res["absolute_change"] == 2_500_000.0
    assert res["percentage_change"] == 25.0
    assert res["direction"] == "positive"
    assert res["reason"] is None


def test_unit_decline():
    """TEST 2: Decline (Prev: 12.5M, Curr: 10M -> -2.5M, -20%, negative)."""
    res = YoYAnalyzer.calculate_field_yoy(previous=12_500_000.0, current=10_000_000.0)
    assert res["status"] == "COMPLETED"
    assert res["absolute_change"] == -2_500_000.0
    assert res["percentage_change"] == -20.0
    assert res["direction"] == "negative"


def test_unit_no_change():
    """TEST 3: No change (Prev: 10M, Curr: 10M -> 0, 0%, unchanged)."""
    res = YoYAnalyzer.calculate_field_yoy(previous=10_000_000.0, current=10_000_000.0)
    assert res["status"] == "COMPLETED"
    assert res["absolute_change"] == 0.0
    assert res["percentage_change"] == 0.0
    assert res["direction"] == "unchanged"


def test_unit_previous_zero():
    """TEST 4: Previous zero (Prev: 0, Curr: 500K -> abs: 500K, pct: None, no crash)."""
    res = YoYAnalyzer.calculate_field_yoy(previous=0.0, current=500_000.0)
    assert res["status"] == "COMPLETED"
    assert res["absolute_change"] == 500_000.0
    assert res["percentage_change"] is None
    assert res["direction"] == "positive"
    assert "zero" in res["reason"].lower()


def test_unit_current_zero():
    """TEST 5: Current zero (Prev: 500K, Curr: 0 -> abs: -500K, pct: -100%, negative)."""
    res = YoYAnalyzer.calculate_field_yoy(previous=500_000.0, current=0.0)
    assert res["status"] == "COMPLETED"
    assert res["absolute_change"] == -500_000.0
    assert res["percentage_change"] == -100.0
    assert res["direction"] == "negative"


def test_unit_missing_previous():
    """TEST 6: Missing previous (Prev: None, Curr: 500K -> status INCOMPLETE)."""
    res = YoYAnalyzer.calculate_field_yoy(previous=None, current=500_000.0)
    assert res["status"] == "INCOMPLETE"
    assert res["absolute_change"] is None
    assert res["percentage_change"] is None
    assert "previous" in res["reason"].lower()


def test_unit_missing_current():
    """TEST 7: Missing current (Prev: 500K, Curr: None -> status INCOMPLETE)."""
    res = YoYAnalyzer.calculate_field_yoy(previous=500_000.0, current=None)
    assert res["status"] == "INCOMPLETE"
    assert res["absolute_change"] is None
    assert res["percentage_change"] is None
    assert "current" in res["reason"].lower()


def test_unit_only_one_period():
    """TEST 8: Only one period provided to analyze_periods returns INSUFFICIENT_DATA."""
    res = YoYAnalyzer.analyze_periods(
        previous_period="2024-25",
        current_period=None,
        previous_metrics={"revenue": 10_000_000.0},
        current_metrics=None,
    )
    assert res["status"] == "INSUFFICIENT_DATA"
    assert "two financial periods" in res["reason"].lower()


def test_unit_negative_values():
    """TEST 9: Negative values calculated mathematically (Prev: -10M, Curr: -5M -> diff: +5M, pct: +50%)."""
    res = YoYAnalyzer.calculate_field_yoy(previous=-10_000_000.0, current=-5_000_000.0)
    assert res["status"] == "COMPLETED"
    assert res["absolute_change"] == 5_000_000.0
    assert res["percentage_change"] == 50.0
    assert res["direction"] == "positive"


def test_unit_large_values():
    """TEST 10: Large financial values (Prev: 1 Trillion, Curr: 1.25 Trillion -> +250 Billion, +25%)."""
    prev_val = 1_000_000_000_000.0
    curr_val = 1_250_000_000_000.0
    res = YoYAnalyzer.calculate_field_yoy(previous=prev_val, current=curr_val)
    assert res["status"] == "COMPLETED"
    assert res["absolute_change"] == 250_000_000_000.0
    assert res["percentage_change"] == 25.0
    assert res["direction"] == "positive"


def test_unit_multiple_financial_fields():
    """TEST 11: Multiple financial fields analyzed concurrently."""
    prev_data = {
        "revenue": 10_000_000.0,
        "assets": 40_000_000.0,
        "liabilities": 15_000_000.0,
        "equity": 25_000_000.0,
    }
    curr_data = {
        "revenue": 12_500_000.0,
        "assets": 45_000_000.0,
        "liabilities": 18_000_000.0,
        "equity": 27_000_000.0,
    }
    res = YoYAnalyzer.analyze_periods(
        previous_period="2023-24",
        current_period="2024-25",
        previous_metrics=prev_data,
        current_metrics=curr_data,
    )
    assert res["status"] == "COMPLETED"
    fin = res["financial_data"]
    assert "revenue" in fin and fin["revenue"]["percentage_change"] == 25.0
    assert "assets" in fin and fin["assets"]["percentage_change"] == 12.5
    assert "liabilities" in fin and fin["liabilities"]["percentage_change"] == 20.0
    assert "equity" in fin and fin["equity"]["percentage_change"] == 8.0


def test_unit_period_ordering():
    """TEST 12: Chronological ordering ensures earlier period is previous, later is current."""
    # Pass 2024-25 as first arg and 2023-24 as second arg
    m_24_25 = {"revenue": 12_500_000.0}
    m_23_24 = {"revenue": 10_000_000.0}
    res = YoYAnalyzer.analyze_periods(
        previous_period="2024-25",
        current_period="2023-24",
        previous_metrics=m_24_25,
        current_metrics=m_23_24,
    )
    assert res["status"] == "COMPLETED"
    assert res["periods"]["previous"] == "2023-24"
    assert res["periods"]["current"] == "2024-25"
    assert res["financial_data"]["revenue"]["previous"] == 10_000_000.0
    assert res["financial_data"]["revenue"]["current"] == 12_500_000.0
    assert res["financial_data"]["revenue"]["percentage_change"] == 25.0


# ==============================================================================
# INTEGRATION TESTS: API POST /api/v1/analysis/{document_id}/yoy
# ==============================================================================

def test_api_valid_normalized_data_two_periods(client: TestClient, db_session: Session):
    """API TEST 1: Valid normalized data with two periods (embedded previous period)."""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="balance_sheet_fy25.pdf",
        file_type="pdf",
        file_path=str(Path("uploads") / "test_fy25.pdf"),
        status=DocumentStatus.NORMALIZED.value
    )
    fin_record = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        company_name="Apex Global Ltd",
        currency="INR",
        fiscal_year="2024-25",
        revenue=12500000.0,
        assets=45000000.0,
        liabilities=18000000.0,
        equity=27000000.0,
        normalized_data={
            "document_id": doc_id,
            "company": {"name": "Apex Global Ltd"},
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
    db_session.add(doc)
    db_session.add(fin_record)
    db_session.commit()

    response = client.post(f"/api/v1/analysis/{doc_id}/yoy")
    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == doc_id
    yoy = data["yoy_analysis"]
    assert yoy["status"] == "COMPLETED"
    assert yoy["periods"]["previous"] == "2023-24"
    assert yoy["periods"]["current"] == "2024-25"
    assert yoy["financial_data"]["revenue"]["absolute_change"] == 2500000.0
    assert yoy["financial_data"]["revenue"]["percentage_change"] == 25.0
    assert yoy["financial_data"]["revenue"]["direction"] == "positive"


def test_api_one_period_only(client: TestClient, db_session: Session):
    """API TEST 2: Only one period available returns INSUFFICIENT_DATA."""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="single_year.csv",
        file_type="csv",
        file_path=str(Path("uploads") / "single_year.csv"),
        status=DocumentStatus.NORMALIZED.value
    )
    fin_record = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        company_name="Unique Startup Inc",
        currency="USD",
        fiscal_year="2024-25",
        revenue=5000000.0,
        assets=10000000.0,
        liabilities=4000000.0,
        equity=6000000.0,
        normalized_data={
            "document_id": doc_id,
            "company": {"name": "Unique Startup Inc"},
            "period": {"fiscal_year": "2024-25"},
            "financial_data": {
                "revenue": 5000000.0,
                "assets": 10000000.0,
                "liabilities": 4000000.0,
                "equity": 6000000.0
            }
        }
    )
    db_session.add(doc)
    db_session.add(fin_record)
    db_session.commit()

    response = client.post(f"/api/v1/analysis/{doc_id}/yoy")
    assert response.status_code == 200
    data = response.json()
    assert data["yoy_analysis"]["status"] == "INSUFFICIENT_DATA"
    assert "at least two financial periods" in data["yoy_analysis"]["reason"].lower()


def test_api_missing_financial_field(client: TestClient, db_session: Session):
    """API TEST 3: Missing financial field produces INCOMPLETE field status."""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="partial_data.xlsx",
        file_type="xlsx",
        file_path=str(Path("uploads") / "partial_data.xlsx"),
        status=DocumentStatus.NORMALIZED.value
    )
    fin_record = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        company_name="Partial Corp",
        currency="INR",
        fiscal_year="2024-25",
        revenue=12000000.0,
        assets=40000000.0,
        liabilities=None,
        equity=None,
        normalized_data={
            "document_id": doc_id,
            "company": {"name": "Partial Corp"},
            "period": {"fiscal_year": "2024-25"},
            "financial_data": {
                "revenue": 12000000.0,
                "assets": 40000000.0,
            },
            "previous_period_data": {
                "fiscal_year": "2023-24",
                "financial_data": {
                    "revenue": 10000000.0,
                    "assets": 35000000.0,
                }
            }
        }
    )
    db_session.add(doc)
    db_session.add(fin_record)
    db_session.commit()

    response = client.post(f"/api/v1/analysis/{doc_id}/yoy")
    assert response.status_code == 200
    data = response.json()
    yoy = data["yoy_analysis"]
    assert yoy["financial_data"]["revenue"]["status"] == "COMPLETED"
    assert yoy["financial_data"]["revenue"]["percentage_change"] == 20.0
    assert yoy["financial_data"]["liabilities"]["status"] == "INCOMPLETE"
    assert yoy["status"] == "INCOMPLETE"


def test_api_zero_previous_value(client: TestClient, db_session: Session):
    """API TEST 4: Zero previous value returns null percentage_change with reason."""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="zero_prev.csv",
        file_type="csv",
        file_path=str(Path("uploads") / "zero_prev.csv"),
        status=DocumentStatus.NORMALIZED.value
    )
    fin_record = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        company_name="New Venture Ltd",
        currency="USD",
        fiscal_year="2024-25",
        revenue=500000.0,
        assets=1000000.0,
        liabilities=400000.0,
        equity=600000.0,
        normalized_data={
            "document_id": doc_id,
            "company": {"name": "New Venture Ltd"},
            "period": {"fiscal_year": "2024-25"},
            "financial_data": {
                "revenue": 500000.0,
                "assets": 1000000.0,
                "liabilities": 400000.0,
                "equity": 600000.0
            },
            "previous_period_data": {
                "fiscal_year": "2023-24",
                "financial_data": {
                    "revenue": 0.0,
                    "assets": 1000000.0,
                    "liabilities": 400000.0,
                    "equity": 600000.0
                }
            }
        }
    )
    db_session.add(doc)
    db_session.add(fin_record)
    db_session.commit()

    response = client.post(f"/api/v1/analysis/{doc_id}/yoy")
    assert response.status_code == 200
    data = response.json()
    rev_result = data["yoy_analysis"]["financial_data"]["revenue"]
    assert rev_result["previous"] == 0.0
    assert rev_result["current"] == 500000.0
    assert rev_result["absolute_change"] == 500000.0
    assert rev_result["percentage_change"] is None
    assert "zero" in rev_result["reason"].lower()


def test_api_nonexistent_document(client: TestClient):
    """API TEST 5: Nonexistent document ID returns 404."""
    nonexistent_id = str(uuid.uuid4())
    response = client.post(f"/api/v1/analysis/{nonexistent_id}/yoy")
    assert response.status_code == 404
    assert f"Document with ID '{nonexistent_id}' not found." in response.json()["detail"]


def test_api_document_not_normalized(client: TestClient, db_session: Session):
    """API TEST 6: Document not in NORMALIZED state returns 400."""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="unprocessed.pdf",
        file_type="pdf",
        file_path=str(Path("uploads") / "unprocessed.pdf"),
        status=DocumentStatus.UPLOADED.value
    )
    db_session.add(doc)
    db_session.commit()

    response = client.post(f"/api/v1/analysis/{doc_id}/yoy")
    assert response.status_code == 400
    assert "has not been normalized yet" in response.json()["detail"]
