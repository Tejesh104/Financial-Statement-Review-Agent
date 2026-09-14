import uuid
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.validation.math_validator import MathValidator, DEFAULT_TOLERANCE
from app.models.document import Document, DocumentStatus
from app.models.financial_data import FinancialData


# ==============================================================================
# UNIT TESTS: MathValidator
# ==============================================================================

def test_unit_valid_balance_sheet():
    """TEST 1: Assets = Liabilities + Equity (45M = 18M + 27M)."""
    res = MathValidator.validate_balance_sheet(
        assets=45000000.0,
        liabilities=18000000.0,
        equity=27000000.0
    )
    assert res["is_valid"] is True
    assert res["status"] == "VALID"
    assert res["difference"] == 0.0
    assert res["liabilities_plus_equity"] == 45000000.0
    assert res["reason"] is None


def test_unit_invalid_balance_sheet():
    """TEST 2: Invalid balance sheet (45M != 20M + 27M = 47M, diff = -2M)."""
    res = MathValidator.validate_balance_sheet(
        assets=45000000.0,
        liabilities=20000000.0,
        equity=27000000.0
    )
    assert res["is_valid"] is False
    assert res["status"] == "INVALID"
    assert res["difference"] == -2000000.0
    assert res["liabilities_plus_equity"] == 47000000.0
    assert "Balance sheet mismatch" in res["reason"]


def test_unit_zero_values():
    """TEST 3: All zeros must be treated as valid numeric values, not missing."""
    res = MathValidator.validate_balance_sheet(
        assets=0.0,
        liabilities=0.0,
        equity=0.0
    )
    assert res["is_valid"] is True
    assert res["status"] == "VALID"
    assert res["difference"] == 0.0
    assert res["liabilities_plus_equity"] == 0.0


def test_unit_missing_assets():
    """TEST 4: Missing assets field returns INCOMPLETE with reason."""
    res = MathValidator.validate_balance_sheet(
        assets=None,
        liabilities=18000000.0,
        equity=27000000.0
    )
    assert res["is_valid"] is None
    assert res["status"] == "INCOMPLETE"
    assert res["difference"] is None
    assert res["liabilities_plus_equity"] is None
    assert "assets" in res["reason"]


def test_unit_missing_liabilities():
    """TEST 5: Missing liabilities field returns INCOMPLETE with reason."""
    res = MathValidator.validate_balance_sheet(
        assets=45000000.0,
        liabilities=None,
        equity=27000000.0
    )
    assert res["is_valid"] is None
    assert res["status"] == "INCOMPLETE"
    assert res["difference"] is None
    assert "liabilities" in res["reason"]


def test_unit_missing_equity():
    """TEST 6: Missing equity field returns INCOMPLETE with reason."""
    res = MathValidator.validate_balance_sheet(
        assets=45000000.0,
        liabilities=18000000.0,
        equity=None
    )
    assert res["is_valid"] is None
    assert res["status"] == "INCOMPLETE"
    assert res["difference"] is None
    assert "equity" in res["reason"]


def test_unit_small_rounding_difference_within_tolerance():
    """TEST 7: Small rounding difference within tolerance is VALID."""
    # diff = 100.005 - 100.0 = 0.005 <= 0.01 tolerance
    res = MathValidator.validate_balance_sheet(
        assets=100.005,
        liabilities=50.0,
        equity=50.0,
        tolerance=0.01
    )
    assert res["is_valid"] is True
    assert res["status"] == "VALID"
    assert abs(res["difference"] - 0.005) < 1e-9


def test_unit_difference_outside_tolerance():
    """TEST 8: Difference exceeding tolerance is INVALID."""
    # diff = 100.05 - 100.0 = 0.05 > 0.01 tolerance
    res = MathValidator.validate_balance_sheet(
        assets=100.05,
        liabilities=50.0,
        equity=50.0,
        tolerance=0.01
    )
    assert res["is_valid"] is False
    assert res["status"] == "INVALID"


def test_unit_negative_value():
    """TEST 9: Negative equity (deficit) is computed algebraically, not rejected."""
    # 10M = 15M + (-5M) = 10M
    res = MathValidator.validate_balance_sheet(
        assets=10000000.0,
        liabilities=15000000.0,
        equity=-5000000.0
    )
    assert res["is_valid"] is True
    assert res["status"] == "VALID"
    assert res["difference"] == 0.0
    assert res["liabilities_plus_equity"] == 10000000.0


def test_unit_large_financial_values():
    """TEST 10: Trillion-scale financial values compute correctly without overflow."""
    assets = 1_000_000_000_000.0
    liabilities = 350_000_000_000.0
    equity = 650_000_000_000.0
    res = MathValidator.validate_balance_sheet(assets, liabilities, equity)
    assert res["is_valid"] is True
    assert res["status"] == "VALID"
    assert res["difference"] == 0.0


# ==============================================================================
# API INTEGRATION TESTS: POST /api/v1/validation/{document_id}/math
# ==============================================================================

def test_api_valid_normalized_document(client: TestClient, db_session: Session):
    """API TEST 1: Valid balance sheet on a normalized document."""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="valid_report.pdf",
        file_type="pdf",
        file_path="uploads/valid_report.pdf",
        status=DocumentStatus.NORMALIZED.value
    )
    fin = FinancialData(
        document_id=doc_id,
        assets=45000000.0,
        liabilities=18000000.0,
        equity=27000000.0,
        normalized_data={"financial_data": {"assets": 45000000.0, "liabilities": 18000000.0, "equity": 27000000.0}}
    )
    db_session.add(doc)
    db_session.add(fin)
    db_session.commit()

    resp = client.post(f"/api/v1/validation/{doc_id}/math")
    assert resp.status_code == 200
    data = resp.json()
    assert data["document_id"] == doc_id
    check = data["balance_sheet_check"]
    assert check["is_valid"] is True
    assert check["status"] == "VALID"
    assert check["assets"] == 45000000.0
    assert check["difference"] == 0.0


def test_api_invalid_normalized_document(client: TestClient, db_session: Session):
    """API TEST 2: Mismatched balance sheet returns 200 with status INVALID."""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="mismatched.pdf",
        file_type="pdf",
        file_path="uploads/mismatched.pdf",
        status=DocumentStatus.NORMALIZED.value
    )
    fin = FinancialData(
        document_id=doc_id,
        assets=50000000.0,
        liabilities=20000000.0,
        equity=25000000.0,  # 20M + 25M = 45M != 50M
        normalized_data={}
    )
    db_session.add(doc)
    db_session.add(fin)
    db_session.commit()

    resp = client.post(f"/api/v1/validation/{doc_id}/math")
    assert resp.status_code == 200
    data = resp.json()
    check = data["balance_sheet_check"]
    assert check["is_valid"] is False
    assert check["status"] == "INVALID"
    assert check["difference"] == 5000000.0


def test_api_missing_financial_field(client: TestClient, db_session: Session):
    """API TEST 3: Document missing equity returns 200 with status INCOMPLETE."""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="missing_field.pdf",
        file_type="pdf",
        file_path="uploads/missing_field.pdf",
        status=DocumentStatus.NORMALIZED.value
    )
    fin = FinancialData(
        document_id=doc_id,
        assets=45000000.0,
        liabilities=18000000.0,
        equity=None,
        normalized_data={}
    )
    db_session.add(doc)
    db_session.add(fin)
    db_session.commit()

    resp = client.post(f"/api/v1/validation/{doc_id}/math")
    assert resp.status_code == 200
    data = resp.json()
    check = data["balance_sheet_check"]
    assert check["is_valid"] is None
    assert check["status"] == "INCOMPLETE"
    assert "equity" in check["reason"]


def test_api_nonexistent_document(client: TestClient):
    """API TEST 4: Nonexistent document ID returns 404."""
    resp = client.post("/api/v1/validation/00000000-0000-0000-0000-000000000000/math")
    assert resp.status_code == 404


def test_api_document_not_normalized(client: TestClient, db_session: Session):
    """API TEST 5: Document in UPLOADED or EXTRACTING status returns 400 Bad Request."""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="unprocessed.pdf",
        file_type="pdf",
        file_path="uploads/unprocessed.pdf",
        status=DocumentStatus.UPLOADED.value
    )
    db_session.add(doc)
    db_session.commit()

    resp = client.post(f"/api/v1/validation/{doc_id}/math")
    assert resp.status_code == 400
    assert "has not been normalized yet" in resp.json()["detail"]
