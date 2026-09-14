"""Unit tests for Agent 2 Metric Comparator."""

from app.services.agent2.metric_comparator import MetricComparator


def test_metric_comparator_revenue_profit():
    findings = {
        "evidence": [
            {"field": "revenue", "value": 1000000.0, "is_available": True},
            {"field": "net_profit", "value": 150000.0, "is_available": True},
            {"field": "gross_profit", "value": 400000.0, "is_available": True},
        ]
    }
    comps = MetricComparator.compare_metrics(findings)
    comp_map = {c["metric_b"]: c for c in comps}
    
    assert "net_profit" in comp_map
    assert comp_map["net_profit"]["relationship"] == "both_positive_profitable"
    assert comp_map["net_profit"]["metric_a_value"] == 1000000.0
    assert comp_map["net_profit"]["metric_b_value"] == 150000.0
    
    assert "gross_profit" in comp_map
    assert comp_map["gross_profit"]["relationship"] == "positive_gross_margin"


def test_metric_comparator_ratios_liquidity_and_leverage():
    findings = {
        "evidence": [
            {"field": "current_assets", "value": 500000.0, "is_available": True},
            {"field": "inventory", "value": 100000.0, "is_available": True},
        ],
        "ratios": [
            {"name": "current_ratio", "status": "COMPLETED", "value": 2.5},
            {"name": "quick_ratio", "status": "COMPLETED", "value": 1.2},
            {"name": "debt_to_equity", "status": "COMPLETED", "value": 0.8},
            {"name": "debt_ratio", "status": "COMPLETED", "value": 0.44},
        ],
        "anomalies": [
            {"is_anomaly": False, "anomaly_score": 0.05}
        ]
    }
    comps = MetricComparator.compare_metrics(findings)
    pairs = {(c["metric_a"], c["metric_b"]): c for c in comps}
    
    assert ("current_assets", "current_ratio") in pairs
    assert pairs[("current_assets", "current_ratio")]["relationship"] == "strong_short_term_liquidity"
    
    assert ("inventory", "quick_ratio") in pairs
    assert pairs[("inventory", "quick_ratio")]["relationship"] == "strong_immediate_liquidity"
    
    assert ("debt_to_equity", "debt_ratio") in pairs
    assert pairs[("debt_to_equity", "debt_ratio")]["relationship"] == "consistent_leverage_profile"


def test_metric_comparator_yoy_divergence():
    findings = {
        "variances": [
            {"field": "revenue", "status": "COMPLETED", "direction": "positive", "percentage_change": 15.0},
            {"field": "net_profit", "status": "COMPLETED", "direction": "negative", "percentage_change": -10.0},
            {"field": "assets", "status": "COMPLETED", "direction": "positive", "percentage_change": 8.0},
            {"field": "equity", "status": "COMPLETED", "direction": "positive", "percentage_change": 8.0},
        ]
    }
    comps = MetricComparator.compare_metrics(findings)
    pairs = {(c["metric_a"], c["metric_b"]): c for c in comps}
    
    assert ("yoy_revenue_percentage_change", "yoy_net_profit_percentage_change") in pairs
    assert pairs[("yoy_revenue_percentage_change", "yoy_net_profit_percentage_change")]["relationship"] == "margin_compression_revenue_up_profit_down"
    
    assert ("yoy_assets_percentage_change", "yoy_equity_percentage_change") in pairs
    assert pairs[("yoy_assets_percentage_change", "yoy_equity_percentage_change")]["relationship"] == "asset_equity_growth_correlation"


def test_metric_comparator_missing_data_no_hallucination():
    # Empty findings should produce empty comparisons without crashing or fabricating
    findings = {}
    comps = MetricComparator.compare_metrics(findings)
    assert len(comps) == 0
