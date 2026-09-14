import json
import uuid
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.database import SessionLocal
from app.models.document import Document, DocumentStatus
from app.models.financial_data import FinancialData
from app.services.agent1.result_builder import Agent1ResultBuilder
from app.services.validation.math_validator import MathValidator
from app.services.analytics.yoy_analyzer import YoYAnalyzer
from app.services.analytics.ratio_analyzer import RatioAnalyzer


# ==============================================================================
# UNIT TESTS
# ==============================================================================

def test_unit_1_complete_agent1_result():
    """TEST 1: Provide valid data for math validation, YoY, and ratios. Result has all 3 sections."""
    doc_id = str(uuid.uuid4())
    current_metrics = {
        "revenue": 1000000.0,
        "gross_profit": 400000.0,
        "net_profit": 150000.0,
        "assets": 2000000.0,
        "liabilities": 800000.0,
        "equity": 1200000.0,
        "current_assets": 600000.0,
        "current_liabilities": 300000.0,
        "inventory": 150000.0,
    }
    previous_metrics = {
        "revenue": 800000.0,
        "gross_profit": 320000.0,
        "net_profit": 120000.0,
        "assets": 1600000.0,
        "liabilities": 700000.0,
        "equity": 900000.0,
        "current_assets": 500000.0,
        "current_liabilities": 250000.0,
        "inventory": 120000.0,
    }
    res = Agent1ResultBuilder.build_from_data(
        document_id=doc_id,
        current_metrics=current_metrics,
        previous_metrics=previous_metrics,
        current_period="2024-25",
        previous_period="2023-24",
    )
    assert res["document_id"] == doc_id
    assert res["agent"] == "Agent 1"
    assert res["status"] == "COMPLETED"
    assert "math_validation" in res["results"]
    assert "yoy_analysis" in res["results"]
    assert "financial_ratios" in res["results"]
    assert res["results"]["math_validation"]["status"] == "VALID"
    assert res["results"]["yoy_analysis"]["status"] == "COMPLETED"
    assert res["results"]["financial_ratios"]["status"] == "COMPLETED"
    assert res["reason"] is None


def test_unit_2_math_validation_invalid():
    """TEST 2: Assets=45M, Liabilities=20M, Equity=27M -> INVALID. Agent 1 returns PARTIAL with other analyses."""
    doc_id = str(uuid.uuid4())
    current_metrics = {
        "revenue": 1000000.0,
        "gross_profit": 400000.0,
        "net_profit": 100000.0,
        "assets": 45000000.0,
        "liabilities": 20000000.0,
        "equity": 27000000.0,
        "current_assets": 500000.0,
        "current_liabilities": 250000.0,
        "inventory": 100000.0,
    }
    previous_metrics = {
        "revenue": 900000.0,
        "gross_profit": 350000.0,
        "net_profit": 80000.0,
        "assets": 40000000.0,
        "liabilities": 18000000.0,
        "equity": 22000000.0,
        "current_assets": 400000.0,
        "current_liabilities": 200000.0,
        "inventory": 80000.0,
    }
    res = Agent1ResultBuilder.build_from_data(
        document_id=doc_id,
        current_metrics=current_metrics,
        previous_metrics=previous_metrics,
        current_period="2024-25",
        previous_period="2023-24",
    )
    assert res["status"] == "PARTIAL"
    assert res["results"]["math_validation"]["status"] == "INVALID"
    assert res["results"]["math_validation"]["is_valid"] is False
    assert res["results"]["yoy_analysis"]["status"] == "COMPLETED"
    assert res["results"]["financial_ratios"]["status"] == "COMPLETED"
    assert any("mismatch" in w.lower() for w in res["warnings"])


def test_unit_3_yoy_insufficient_data():
    """TEST 3: Provide only 1 period. YoY is INSUFFICIENT_DATA. Agent 1 does not crash, returns PARTIAL."""
    doc_id = str(uuid.uuid4())
    current_metrics = {
        "revenue": 1000000.0,
        "gross_profit": 400000.0,
        "net_profit": 100000.0,
        "assets": 2000000.0,
        "liabilities": 800000.0,
        "equity": 1200000.0,
        "current_assets": 400000.0,
        "current_liabilities": 200000.0,
        "inventory": 100000.0,
    }
    res = Agent1ResultBuilder.build_from_data(
        document_id=doc_id,
        current_metrics=current_metrics,
        previous_metrics=None,
        current_period="2024-25",
        previous_period=None,
    )
    assert res["status"] == "PARTIAL"
    assert res["results"]["yoy_analysis"]["status"] == "INSUFFICIENT_DATA"
    assert res["results"]["math_validation"]["status"] == "VALID"
    assert res["results"]["financial_ratios"]["status"] == "COMPLETED"


def test_unit_4_ratio_incomplete():
    """TEST 4: Missing required ratio fields. financial_ratios is INCOMPLETE. Agent 1 returns other results."""
    doc_id = str(uuid.uuid4())
    # Omit current_liabilities and revenue
    current_metrics = {
        "assets": 1000000.0,
        "liabilities": 400000.0,
        "equity": 600000.0,
    }
    previous_metrics = {
        "assets": 800000.0,
        "liabilities": 300000.0,
        "equity": 500000.0,
    }
    res = Agent1ResultBuilder.build_from_data(
        document_id=doc_id,
        current_metrics=current_metrics,
        previous_metrics=previous_metrics,
        current_period="2024-25",
        previous_period="2023-24",
    )
    assert res["status"] == "PARTIAL"
    assert res["results"]["financial_ratios"]["status"] == "INCOMPLETE"
    assert res["results"]["math_validation"]["status"] == "VALID"
    assert res["results"]["yoy_analysis"]["status"] == "COMPLETED"


def test_unit_5_zero_denominator():
    """TEST 5: Zero revenue/assets/equity -> ratios remain UNDEFINED, no NaN or Infinity."""
    doc_id = str(uuid.uuid4())
    current_metrics = {
        "revenue": 0.0,
        "gross_profit": 50000.0,
        "net_profit": 20000.0,
        "assets": 1000000.0,
        "liabilities": 400000.0,
        "equity": 600000.0,
        "current_assets": 200000.0,
        "current_liabilities": 100000.0,
        "inventory": 50000.0,
    }
    res = Agent1ResultBuilder.build_from_data(
        document_id=doc_id,
        current_metrics=current_metrics,
        previous_metrics=None,
    )
    gpm = res["results"]["financial_ratios"]["ratios"]["profitability"]["gross_profit_margin"]
    assert gpm["status"] == "UNDEFINED"
    assert gpm["value"] is None
    dumped = json.dumps(res)
    assert "NaN" not in dumped
    assert "Infinity" not in dumped


def test_unit_6_missing_fields_no_fabrication():
    """TEST 6: Partial normalized dataset. Agent 1 returns structured partial results without fabricated values."""
    doc_id = str(uuid.uuid4())
    current_metrics = {
        "revenue": 500000.0,
    }
    res = Agent1ResultBuilder.build_from_data(
        document_id=doc_id,
        current_metrics=current_metrics,
    )
    assert res["status"] == "PARTIAL"
    assert res["results"]["math_validation"]["status"] == "INCOMPLETE"
    assert res["results"]["math_validation"]["assets"] is None
    assert res["results"]["financial_ratios"]["ratios"]["liquidity"]["current_ratio"]["value"] is None


def test_unit_7_negative_financial_values():
    """TEST 7: Handles negative net profit correctly and preserves calculations."""
    doc_id = str(uuid.uuid4())
    current_metrics = {
        "revenue": 1000000.0,
        "gross_profit": 200000.0,
        "net_profit": -50000.0,
        "assets": 1000000.0,
        "liabilities": 400000.0,
        "equity": 600000.0,
        "current_assets": 200000.0,
        "current_liabilities": 100000.0,
        "inventory": 50000.0,
    }
    previous_metrics = {
        "revenue": 800000.0,
        "gross_profit": 150000.0,
        "net_profit": 10000.0,
        "assets": 900000.0,
        "liabilities": 400000.0,
        "equity": 500000.0,
    }
    res = Agent1ResultBuilder.build_from_data(
        document_id=doc_id,
        current_metrics=current_metrics,
        previous_metrics=previous_metrics,
        current_period="2024-25",
        previous_period="2023-24",
    )
    npm = res["results"]["financial_ratios"]["ratios"]["profitability"]["net_profit_margin"]
    assert npm["status"] == "COMPLETED"
    assert npm["value"] == -5.0


def test_unit_8_large_financial_values():
    """TEST 8: Handles large trillion-scale values without precision overflow."""
    doc_id = str(uuid.uuid4())
    current_metrics = {
        "revenue": 1250000000000.0,
        "gross_profit": 500000000000.0,
        "net_profit": 250000000000.0,
        "assets": 5000000000000.0,
        "liabilities": 2000000000000.0,
        "equity": 3000000000000.0,
        "current_assets": 1000000000000.0,
        "current_liabilities": 500000000000.0,
        "inventory": 200000000000.0,
    }
    previous_metrics = {
        "revenue": 1000000000000.0,
        "gross_profit": 400000000000.0,
        "net_profit": 200000000000.0,
        "assets": 4000000000000.0,
        "liabilities": 1500000000000.0,
        "equity": 2500000000000.0,
        "current_assets": 800000000000.0,
        "current_liabilities": 400000000000.0,
        "inventory": 150000000000.0,
    }
    res = Agent1ResultBuilder.build_from_data(
        document_id=doc_id,
        current_metrics=current_metrics,
        previous_metrics=previous_metrics,
        current_period="2024-25",
        previous_period="2023-24",
    )
    assert res["status"] == "COMPLETED"
    assert res["results"]["math_validation"]["is_valid"] is True
    assert res["results"]["financial_ratios"]["ratios"]["profitability"]["gross_profit_margin"]["value"] == 40.0


def test_unit_9_warning_aggregation():
    """TEST 9: Aggregates warnings from math validation, YoY, and ratios without duplicates."""
    doc_id = str(uuid.uuid4())
    current_metrics = {
        "revenue": 0.0,  # Causes ratio undefined warning
        "gross_profit": 10000.0,
        "assets": 1000.0,
        "liabilities": 200.0,
        "equity": 200.0,  # Causes math invalid warning (1000 != 400)
    }
    res = Agent1ResultBuilder.build_from_data(
        document_id=doc_id,
        current_metrics=current_metrics,
        previous_metrics=None,
    )
    assert len(res["warnings"]) >= 2
    # Ensure warnings are strings and deduplicated
    assert len(res["warnings"]) == len(set(res["warnings"]))


def test_unit_10_no_duplicate_calculations():
    """TEST 10: Verify Agent 1 delegates to MathValidator, YoYAnalyzer, and RatioAnalyzer."""
    with patch.object(MathValidator, "validate_balance_sheet", wraps=MathValidator.validate_balance_sheet) as mock_math, \
         patch.object(YoYAnalyzer, "analyze_periods", wraps=YoYAnalyzer.analyze_periods) as mock_yoy, \
         patch.object(RatioAnalyzer, "analyze_ratios", wraps=RatioAnalyzer.analyze_ratios) as mock_ratios:

        Agent1ResultBuilder.build_from_data(
            document_id="test-doc",
            current_metrics={"revenue": 100.0, "assets": 200.0, "liabilities": 80.0, "equity": 120.0},
            previous_metrics={"revenue": 80.0, "assets": 150.0, "liabilities": 60.0, "equity": 90.0},
            current_period="2024-25",
            previous_period="2023-24",
        )
        assert mock_math.called
        assert mock_yoy.called
        assert mock_ratios.called


def test_unit_11_json_serialization():
    """TEST 11: Verify the complete Agent 1 result can be serialized cleanly to JSON."""
    doc_id = str(uuid.uuid4())
    current_metrics = {
        "revenue": 1000000.0,
        "assets": 2000000.0,
        "liabilities": 800000.0,
        "equity": 1200000.0,
    }
    res = Agent1ResultBuilder.build_from_data(
        document_id=doc_id,
        current_metrics=current_metrics,
    )
    json_str = json.dumps(res)
    assert json_str is not None
    deserialized = json.loads(json_str)
    assert deserialized["document_id"] == doc_id


def test_unit_12_result_structure():
    """TEST 12: Verify document_id, agent, status, results, warnings, reason are present."""
    doc_id = str(uuid.uuid4())
    res = Agent1ResultBuilder.build_from_data(
        document_id=doc_id,
        current_metrics={"revenue": 1000.0},
    )
    assert "document_id" in res
    assert "agent" in res
    assert "status" in res
    assert "results" in res
    assert "warnings" in res
    assert "reason" in res


# ==============================================================================
# API TESTS
# ==============================================================================

@pytest.fixture
def test_client():
    return TestClient(app)


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_api_valid_normalized_document(test_client, db_session):
    """API 1 & 2: Valid normalized document produces HTTP 200 with complete results."""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="agent1_full.csv",
        file_type="csv",
        file_path=str(Path("uploads") / "agent1_full.csv"),
        status=DocumentStatus.NORMALIZED.value,
    )
    fin = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        company_name="Tata Consultancy Services Ltd",
        currency="INR",
        fiscal_year="2024-25",
        revenue=1000000.0,
        assets=2000000.0,
        liabilities=800000.0,
        equity=1200000.0,
        normalized_data={
            "document_id": doc_id,
            "company": {"name": "Tata Consultancy Services Ltd"},
            "currency": "INR",
            "period": {"fiscal_year": "2024-25"},
            "previous_period_data": {
                "period": "2023-24",
                "financial_data": {
                    "revenue": 800000.0,
                    "gross_profit": 350000.0,
                    "net_profit": 150000.0,
                    "assets": 1600000.0,
                    "liabilities": 600000.0,
                    "equity": 1000000.0,
                    "current_assets": 500000.0,
                    "current_liabilities": 250000.0,
                    "inventory": 80000.0,
                }
            },
            "financial_data": {
                "revenue": 1000000.0,
                "gross_profit": 450000.0,
                "net_profit": 200000.0,
                "assets": 2000000.0,
                "liabilities": 800000.0,
                "equity": 1200000.0,
                "current_assets": 600000.0,
                "current_liabilities": 300000.0,
                "inventory": 100000.0,
            }
        }
    )
    db_session.add(doc)
    db_session.add(fin)
    db_session.commit()

    resp = test_client.post(f"/api/v1/agent1/{doc_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["document_id"] == doc_id
    assert data["agent"] == "Agent 1"
    assert data["status"] == "COMPLETED"
    assert "math_validation" in data["results"]
    assert "yoy_analysis" in data["results"]
    assert "financial_ratios" in data["results"]

    # Test alias route /api/v1/analysis/{document_id}/agent1
    resp_alias = test_client.post(f"/api/v1/analysis/{doc_id}/agent1")
    assert resp_alias.status_code == 200
    assert resp_alias.json()["document_id"] == doc_id


def test_api_partial_financial_data(test_client, db_session):
    """API 3: Partial financial data returns HTTP 200 with PARTIAL status."""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="partial_doc.csv",
        file_type="csv",
        file_path=str(Path("uploads") / "partial_doc.csv"),
        status=DocumentStatus.NORMALIZED.value,
    )
    fin = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        company_name="Partial Corp",
        currency="USD",
        revenue=500000.0,
        normalized_data={
            "document_id": doc_id,
            "financial_data": {"revenue": 500000.0}
        }
    )
    db_session.add(doc)
    db_session.add(fin)
    db_session.commit()

    resp = test_client.post(f"/api/v1/agent1/{doc_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "PARTIAL"
    assert data["results"]["math_validation"]["status"] == "INCOMPLETE"


def test_api_nonexistent_document(test_client):
    """API 4: Nonexistent document returns HTTP 404."""
    resp = test_client.post(f"/api/v1/agent1/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_api_unnormalized_document(test_client, db_session):
    """API 5: Unnormalized document returns HTTP 400."""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="raw.pdf",
        file_type="pdf",
        file_path="uploads/raw.pdf",
        status=DocumentStatus.UPLOADED.value,
    )
    db_session.add(doc)
    db_session.commit()

    resp = test_client.post(f"/api/v1/agent1/{doc_id}")
    assert resp.status_code == 400


def test_api_database_persistence(test_client, db_session):
    """API 7: Result is persisted under normalized_data['analysis']['agent1']."""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="persist_test.csv",
        file_type="csv",
        file_path="uploads/persist_test.csv",
        status=DocumentStatus.NORMALIZED.value,
    )
    fin = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        company_name="Persist Corp",
        currency="USD",
        revenue=100000.0,
        assets=200000.0,
        liabilities=80000.0,
        equity=120000.0,
        normalized_data={
            "document_id": doc_id,
            "financial_data": {
                "revenue": 100000.0,
                "assets": 200000.0,
                "liabilities": 80000.0,
                "equity": 120000.0,
            },
            "analysis": {
                "yoy": {"existing_yoy": True},
                "ratios": {"existing_ratios": True},
            }
        }
    )
    db_session.add(doc)
    db_session.add(fin)
    db_session.commit()

    resp = test_client.post(f"/api/v1/agent1/{doc_id}")
    assert resp.status_code == 200

    db_session.refresh(fin)
    analysis_block = fin.normalized_data.get("analysis", {})
    assert "agent1" in analysis_block
    assert analysis_block["agent1"]["status"] is not None
    # Verify existing analysis blocks were NOT deleted
    assert "yoy" in analysis_block
    assert "ratios" in analysis_block


def test_api_existing_endpoints_regression(test_client, db_session):
    """API 8, 9, 10: Existing Math, YoY, and Ratios endpoints continue to work."""
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="regress.csv",
        file_type="csv",
        file_path="uploads/regress.csv",
        status=DocumentStatus.NORMALIZED.value,
    )
    fin = FinancialData(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        company_name="Regress Corp",
        revenue=100000.0,
        assets=200000.0,
        liabilities=80000.0,
        equity=120000.0,
        normalized_data={
            "document_id": doc_id,
            "financial_data": {
                "revenue": 100000.0,
                "assets": 200000.0,
                "liabilities": 80000.0,
                "equity": 120000.0,
            }
        }
    )
    db_session.add(doc)
    db_session.add(fin)
    db_session.commit()

    # Math endpoint
    r_math = test_client.post(f"/api/v1/validation/{doc_id}/math")
    assert r_math.status_code == 200

    # YoY endpoint
    r_yoy = test_client.post(f"/api/v1/analysis/{doc_id}/yoy")
    assert r_yoy.status_code == 200

    # Ratios endpoint
    r_ratios = test_client.post(f"/api/v1/analysis/{doc_id}/ratios")
    assert r_ratios.status_code == 200
