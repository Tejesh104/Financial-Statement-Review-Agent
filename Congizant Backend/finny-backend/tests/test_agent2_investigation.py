"""Unit tests for Agent 2 Investigation Service."""

from app.services.agent2.investigation import InvestigationService


def test_investigate_valid_balance_sheet():
    findings = {
        "validations": [{
            "type": "BALANCE_SHEET_VALIDATION",
            "status": "VALID",
            "difference": 0.0,
            "tolerance": 0.01,
            "reason": None,
        }]
    }
    res = InvestigationService.investigate(findings)
    assert len(res) >= 1
    val_item = [i for i in res if i["category"] == "VALIDATION"][0]
    assert val_item["status"] == "VALID"
    assert "equation holds" in val_item["description"]
    assert val_item["reason"] is None


def test_investigate_invalid_balance_sheet():
    findings = {
        "validations": [{
            "type": "BALANCE_SHEET_VALIDATION",
            "status": "INVALID",
            "difference": 150000.0,
            "tolerance": 0.01,
            "reason": "Assets != Liabilities + Equity",
        }]
    }
    res = InvestigationService.investigate(findings)
    val_item = [i for i in res if i["category"] == "VALIDATION"][0]
    assert val_item["status"] == "INVALID"
    assert "150000.00" in val_item["description"]
    assert val_item["reason"] == "Assets != Liabilities + Equity"


def test_investigate_yoy_growth_and_decline():
    findings = {
        "variances": [
            {
                "field": "revenue",
                "current_period": "2024",
                "previous_period": "2023",
                "current_value": 1200000.0,
                "previous_value": 1000000.0,
                "absolute_change": 200000.0,
                "percentage_change": 20.0,
                "direction": "positive",
                "status": "COMPLETED",
            },
            {
                "field": "net_profit",
                "current_period": "2024",
                "previous_period": "2023",
                "current_value": 80000.0,
                "previous_value": 100000.0,
                "absolute_change": -20000.0,
                "percentage_change": -20.0,
                "direction": "negative",
                "status": "COMPLETED",
            }
        ]
    }
    res = InvestigationService.investigate(findings)
    yoy_items = [i for i in res if i["category"] == "YOY"]
    assert len(yoy_items) == 2
    assert "increased by" in yoy_items[0]["description"]
    assert "decreased by" in yoy_items[1]["description"]


def test_investigate_yoy_insufficient_data():
    findings = {"variances": []}
    res = InvestigationService.investigate(findings)
    yoy_item = [i for i in res if i["category"] == "YOY"][0]
    assert yoy_item["status"] == "INSUFFICIENT_DATA"
    assert "fewer than two financial periods" in yoy_item["description"]


def test_investigate_ml_normal_and_anomaly():
    findings_normal = {
        "anomalies": [{
            "classification": "NORMAL",
            "is_anomaly": False,
            "anomaly_score": 0.08,
            "model_type": "IsolationForest",
        }]
    }
    res_norm = InvestigationService.investigate(findings_normal)
    item_norm = [i for i in res_norm if i["category"] == "ML_ANOMALY"][0]
    assert item_norm["status"] == "NORMAL"
    assert "Statistical normality confirmed" in item_norm["description"]

    findings_anom = {
        "anomalies": [{
            "classification": "ANOMALY",
            "is_anomaly": True,
            "anomaly_score": -0.19,
            "model_type": "IsolationForest",
            "reason": "Extreme leverage feature values",
        }]
    }
    res_anom = InvestigationService.investigate(findings_anom)
    item_anom = [i for i in res_anom if i["category"] == "ML_ANOMALY"][0]
    assert item_anom["status"] == "ANOMALY"
    assert "Statistical anomaly flagged" in item_anom["description"]
    assert item_anom["reason"] == "Extreme leverage feature values"


def test_investigate_ratios_states():
    findings = {
        "ratios": [
            {"name": "current_ratio", "category": "liquidity", "status": "COMPLETED", "value": 2.15},
            {"name": "quick_ratio", "category": "liquidity", "status": "UNDEFINED", "value": None, "reason": "Zero inventory denominator"},
            {"name": "debt_to_equity", "category": "leverage", "status": "INCOMPLETE", "value": None, "reason": "Missing equity"},
        ]
    }
    res = InvestigationService.investigate(findings)
    ratio_items = [i for i in res if i["category"] == "RATIO"]
    assert len(ratio_items) == 3
    assert ratio_items[0]["status"] == "COMPLETED"
    assert "2.15" in ratio_items[0]["description"]
    assert ratio_items[1]["status"] == "UNDEFINED"
    assert ratio_items[2]["status"] == "INCOMPLETE"


def test_investigate_missing_evidence():
    findings = {
        "evidence": [
            {"field": "revenue", "value": 1000.0, "is_available": True},
            {"field": "inventory", "value": None, "is_available": False},
        ]
    }
    res = InvestigationService.investigate(findings)
    ev_item = [i for i in res if i["category"] == "EVIDENCE"][0]
    assert ev_item["status"] == "PARTIAL"
    assert "inventory" in ev_item["description"]
