import uuid
import copy
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database.database import SessionLocal
from app.models.document import Document, DocumentStatus
from app.models.financial_data import FinancialData
from app.services.analytics.ratio_analyzer import RatioAnalyzer


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_sample_normalized_doc(db: Session, status=DocumentStatus.NORMALIZED.value):
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="hardening_sample.csv",
        file_type="csv",
        file_path=str(Path("uploads") / "hardening_sample.csv"),
        status=status,
    )
    db.add(doc)
    fin = None
    if status == DocumentStatus.NORMALIZED.value:
        fin = FinancialData(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            company_name="Hardening Corp",
            currency="USD",
            fiscal_year="2024-25",
            revenue=1000000.0,
            assets=2000000.0,
            liabilities=800000.0,
            equity=1200000.0,
            normalized_data={
                "document_id": doc_id,
                "company": {"name": "Hardening Corp"},
                "currency": "USD",
                "period": {"fiscal_year": "2024-25"},
                "previous_period_data": {
                    "period": "2023-24",
                    "financial_data": {
                        "revenue": 800000.0,
                        "assets": 1600000.0,
                        "liabilities": 600000.0,
                        "equity": 1000000.0,
                    }
                },
                "financial_data": {
                    "revenue": 1000000.0,
                    "gross_profit": 400000.0,
                    "net_profit": 150000.0,
                    "assets": 2000000.0,
                    "equity": 1200000.0,
                    "liabilities": 800000.0,
                    "current_assets": 600000.0,
                    "current_liabilities": 300000.0,
                    "inventory": 150000.0,
                }
            }
        )
        db.add(fin)
    db.commit()
    return doc, fin


# ==============================================================================
# 1. UUID & DOCUMENT STATE VALIDATION TESTS
# ==============================================================================

def test_hardening_invalid_uuid_returns_400(client: TestClient):
    """Invalid UUID string returns HTTP 400 Bad Request across all analytics endpoints."""
    bad_id = "invalid-uuid-12345"
    assert client.post(f"/api/v1/validation/{bad_id}/math").status_code == 400
    assert client.post(f"/api/v1/analysis/{bad_id}/yoy").status_code == 400
    assert client.post(f"/api/v1/analysis/{bad_id}/ratios").status_code == 400
    assert client.post(f"/api/v1/agent1/{bad_id}").status_code == 400
    assert client.post(f"/api/v1/analysis/{bad_id}/agent1").status_code == 400


def test_hardening_nonexistent_valid_uuid_returns_404(client: TestClient):
    """Valid UUID that does not exist in DB returns HTTP 404 Not Found."""
    nonexistent = str(uuid.uuid4())
    assert client.post(f"/api/v1/validation/{nonexistent}/math").status_code == 404
    assert client.post(f"/api/v1/analysis/{nonexistent}/yoy").status_code == 404
    assert client.post(f"/api/v1/analysis/{nonexistent}/ratios").status_code == 404
    assert client.post(f"/api/v1/agent1/{nonexistent}").status_code == 404
    assert client.post(f"/api/v1/analysis/{nonexistent}/agent1").status_code == 404


def test_hardening_unnormalized_document_states_return_400(client: TestClient, db_session: Session):
    """All unnormalized document states return HTTP 400."""
    unnormalized_states = [
        DocumentStatus.UPLOADED.value,
        DocumentStatus.EXTRACTING.value,
        DocumentStatus.EXTRACTED.value,
        DocumentStatus.NORMALIZING.value,
        DocumentStatus.EXTRACTION_FAILED.value,
        DocumentStatus.NORMALIZATION_FAILED.value,
    ]
    for st in unnormalized_states:
        doc, _ = create_sample_normalized_doc(db_session, status=st)
        res_math = client.post(f"/api/v1/validation/{doc.id}/math")
        assert res_math.status_code == 400
        assert "has not been normalized yet" in res_math.json()["detail"]

        res_yoy = client.post(f"/api/v1/analysis/{doc.id}/yoy")
        assert res_yoy.status_code == 400

        res_ratios = client.post(f"/api/v1/analysis/{doc.id}/ratios")
        assert res_ratios.status_code == 400

        res_agent1 = client.post(f"/api/v1/agent1/{doc.id}")
        assert res_agent1.status_code == 400


def test_hardening_missing_financial_record_returns_404(client: TestClient, db_session: Session):
    """Document is NORMALIZED but has no FinancialData row -> HTTP 404."""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="orphan.csv",
        file_type="csv",
        file_path="uploads/orphan.csv",
        status=DocumentStatus.NORMALIZED.value
    )
    db_session.add(doc)
    db_session.commit()

    assert client.post(f"/api/v1/validation/{doc_id}/math").status_code == 404
    assert client.post(f"/api/v1/analysis/{doc_id}/yoy").status_code == 404
    assert client.post(f"/api/v1/analysis/{doc_id}/ratios").status_code == 404
    assert client.post(f"/api/v1/agent1/{doc_id}").status_code == 404


# ==============================================================================
# 2. MALFORMED VALUES & ZERO DENOMINATOR TESTS
# ==============================================================================

def test_hardening_malformed_numeric_strings_handled_safely(client: TestClient, db_session: Session):
    """Non-numeric string values in financial fields do not crash the server and are treated as None."""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="malformed.csv",
        file_type="csv",
        file_path="uploads/malformed.csv",
        status=DocumentStatus.NORMALIZED.value
    )
    fin = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        company_name="Malformed Corp",
        revenue=None,
        assets=None,
        liabilities=None,
        equity=None,
        normalized_data={
            "document_id": doc_id,
            "financial_data": {
                "revenue": "not_a_number",
                "gross_profit": "corrupt_data",
                "assets": "invalid_float",
            }
        }
    )
    db_session.add(doc)
    db_session.add(fin)
    db_session.commit()

    # Math
    r_math = client.post(f"/api/v1/validation/{doc_id}/math")
    assert r_math.status_code == 200
    assert r_math.json()["balance_sheet_check"]["status"] == "INCOMPLETE"

    # Ratios
    r_ratios = client.post(f"/api/v1/analysis/{doc_id}/ratios")
    assert r_ratios.status_code == 200
    assert r_ratios.json()["ratio_analysis"]["status"] == "INCOMPLETE"

    # Agent 1
    r_agent1 = client.post(f"/api/v1/agent1/{doc_id}")
    assert r_agent1.status_code == 200
    assert r_agent1.json()["status"] == "PARTIAL"


def test_hardening_zero_denominator_no_nan_or_inf(client: TestClient, db_session: Session):
    """Zero denominator produces UNDEFINED without NaN or Infinity in responses."""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="zero_den.csv",
        file_type="csv",
        file_path="uploads/zero_den.csv",
        status=DocumentStatus.NORMALIZED.value
    )
    fin = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        revenue=0.0,
        assets=0.0,
        liabilities=0.0,
        equity=0.0,
        normalized_data={
            "document_id": doc_id,
            "financial_data": {
                "revenue": 0.0,
                "gross_profit": 1000.0,
                "assets": 0.0,
                "equity": 0.0,
                "current_assets": 500.0,
                "current_liabilities": 0.0,
            }
        }
    )
    db_session.add(doc)
    db_session.add(fin)
    db_session.commit()

    r = client.post(f"/api/v1/analysis/{doc_id}/ratios")
    assert r.status_code == 200
    body_text = r.text
    assert "NaN" not in body_text
    assert "Infinity" not in body_text
    data = r.json()
    cr = data["ratio_analysis"]["ratios"]["liquidity"]["current_ratio"]
    assert cr["status"] == "UNDEFINED"
    assert cr["value"] is None


# ==============================================================================
# 3. DATABASE PERSISTENCE, PRESERVATION & REPEATABILITY TESTS
# ==============================================================================

def test_hardening_persistence_preservation(client: TestClient, db_session: Session):
    """Running each endpoint sequentially preserves all existing normalized and analytical blocks."""
    doc, fin = create_sample_normalized_doc(db_session)

    # 1. Run Math Validation
    r_math = client.post(f"/api/v1/validation/{doc.id}/math")
    assert r_math.status_code == 200
    db_session.refresh(fin)
    assert "validation" in fin.normalized_data
    assert "financial_data" in fin.normalized_data

    # 2. Run YoY Analysis
    r_yoy = client.post(f"/api/v1/analysis/{doc.id}/yoy")
    assert r_yoy.status_code == 200
    db_session.refresh(fin)
    assert "validation" in fin.normalized_data
    assert "yoy" in fin.normalized_data["analysis"]

    # 3. Run Ratios
    r_ratios = client.post(f"/api/v1/analysis/{doc.id}/ratios")
    assert r_ratios.status_code == 200
    db_session.refresh(fin)
    assert "validation" in fin.normalized_data
    assert "yoy" in fin.normalized_data["analysis"]
    assert "ratios" in fin.normalized_data["analysis"]

    # 4. Run Agent 1
    r_agent1 = client.post(f"/api/v1/agent1/{doc.id}")
    assert r_agent1.status_code == 200
    db_session.refresh(fin)
    assert "validation" in fin.normalized_data
    assert "yoy" in fin.normalized_data["analysis"]
    assert "ratios" in fin.normalized_data["analysis"]
    assert "agent1" in fin.normalized_data["analysis"]

    # Document status remained NORMALIZED throughout
    db_session.refresh(doc)
    assert doc.status == DocumentStatus.NORMALIZED.value


def test_hardening_repeated_execution_no_duplicate_rows(client: TestClient, db_session: Session):
    """Calling endpoints repeatedly updates records in place without duplicating FinancialData rows."""
    doc, fin = create_sample_normalized_doc(db_session)
    count_before = db_session.query(FinancialData).filter(FinancialData.document_id == doc.id).count()
    assert count_before == 1

    # Execute all endpoints twice
    for _ in range(2):
        client.post(f"/api/v1/validation/{doc.id}/math")
        client.post(f"/api/v1/analysis/{doc.id}/yoy")
        client.post(f"/api/v1/analysis/{doc.id}/ratios")
        client.post(f"/api/v1/agent1/{doc.id}")

    count_after = db_session.query(FinancialData).filter(FinancialData.document_id == doc.id).count()
    assert count_after == 1


def test_hardening_database_rollback_on_failure(client: TestClient, db_session: Session):
    """Database commit failure triggers rollback and clean HTTP 500 error."""
    from app.database.database import get_db

    doc, fin = create_sample_normalized_doc(db_session)

    def failing_get_db():
        yield db_session

    app.dependency_overrides[get_db] = failing_get_db
    try:
        with patch.object(db_session, "commit", side_effect=Exception("Database lock error")):
            r = client.post(f"/api/v1/agent1/{doc.id}")
            assert r.status_code == 500
            assert "Failed to persist agent1 analysis" in r.json()["detail"]
    finally:
        app.dependency_overrides.clear()


# ==============================================================================
# 4. FINANCIAL RATIO DEBT FIELD DISTINCTION TESTS
# ==============================================================================

def test_hardening_ratio_explicit_debt_precedence():
    """When both debt and liabilities are provided, explicit debt takes precedence."""
    metrics = {
        "debt": 500.0,
        "liabilities": 1000.0,
        "equity": 500.0,
        "assets": 2000.0,
    }
    res = RatioAnalyzer.analyze_ratios(metrics)
    # Debt-to-Equity = 500 / 500 = 1.0 (not 1000 / 500 = 2.0)
    assert res["ratios"]["leverage"]["debt_to_equity"]["value"] == 1.0
    # Debt Ratio = 500 / 2000 = 0.25 (not 1000 / 2000 = 0.5)
    assert res["ratios"]["leverage"]["debt_ratio"]["value"] == 0.25


def test_hardening_ratio_missing_debt_and_liabilities():
    """When neither debt nor liabilities is provided, leverage ratios are INCOMPLETE without fabricating values."""
    metrics = {
        "equity": 500.0,
        "assets": 2000.0,
    }
    res = RatioAnalyzer.analyze_ratios(metrics)
    dte = res["ratios"]["leverage"]["debt_to_equity"]
    dr = res["ratios"]["leverage"]["debt_ratio"]
    assert dte["status"] == "INCOMPLETE"
    assert dte["value"] is None
    assert dr["status"] == "INCOMPLETE"
    assert dr["value"] is None
