"""Metric comparator service for Agent 2.

Compares ONLY verified metrics already present in Agent 1 Findings.
Zero recalculation, no fabricated metrics, no new ratios.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MetricComparator:
    """Compares verified metrics deterministically without altering numerical values."""

    @classmethod
    def compare_metrics(cls, findings: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Perform pairwise comparisons across allowed metric relationships.

        Allowed comparisons:
          1. Revenue ↔ Net Profit
          2. Revenue ↔ Gross Profit
          3. Net Profit ↔ Net Profit Margin
          4. Assets ↔ ROA (Return on Assets)
          5. Equity ↔ ROE (Return on Equity)
          6. Debt-to-Equity ↔ Debt Ratio
          7. Current Assets ↔ Current Ratio
          8. Current Assets / Inventory ↔ Quick Ratio
          9. YoY Revenue ↔ YoY Net Profit
          10. YoY Assets ↔ YoY Equity
          11. ML anomaly status ↔ corresponding ratios

        Args:
            findings: Dict with 'validations', 'variances', 'anomalies', 'ratios', 'evidence'.

        Returns:
            List of MetricComparisonItem dicts.
        """
        comparisons: List[Dict[str, Any]] = []

        # 1. Map available evidence values
        ev_map: Dict[str, Optional[float]] = {}
        for ev in findings.get("evidence", []):
            if ev.get("is_available") and ev.get("value") is not None:
                ev_map[ev["field"]] = float(ev["value"])

        # 2. Map available ratios
        ratio_map: Dict[str, Optional[float]] = {}
        for r in findings.get("ratios", []):
            if r.get("status") == "COMPLETED" and r.get("value") is not None:
                ratio_map[r["name"]] = float(r["value"])

        # 3. Map available YoY variances
        yoy_map: Dict[str, Dict[str, Any]] = {}
        for v in findings.get("variances", []):
            if v.get("status") == "COMPLETED":
                yoy_map[v["field"]] = v

        # -------------------------------------------------------------
        # Relationship 1: Revenue ↔ Net Profit
        # -------------------------------------------------------------
        rev = ev_map.get("revenue")
        np = ev_map.get("net_profit")
        if rev is not None and np is not None:
            if rev > 0 and np > 0:
                rel = "both_positive_profitable"
            elif rev > 0 and np <= 0:
                rel = "positive_revenue_net_loss"
            elif rev <= 0 and np <= 0:
                rel = "both_non_positive"
            else:
                rel = "negative_revenue_positive_profit"
            comparisons.append({
                "metric_a": "revenue",
                "metric_a_value": rev,
                "metric_b": "net_profit",
                "metric_b_value": np,
                "relationship": rel,
                "evidence": ["findings.evidence.revenue", "findings.evidence.net_profit"],
            })

        # -------------------------------------------------------------
        # Relationship 2: Revenue ↔ Gross Profit
        # -------------------------------------------------------------
        gp = ev_map.get("gross_profit")
        if rev is not None and gp is not None:
            rel = "positive_gross_margin" if (gp > 0 and rev > 0) else "non_positive_gross_profit"
            comparisons.append({
                "metric_a": "revenue",
                "metric_a_value": rev,
                "metric_b": "gross_profit",
                "metric_b_value": gp,
                "relationship": rel,
                "evidence": ["findings.evidence.revenue", "findings.evidence.gross_profit"],
            })

        # -------------------------------------------------------------
        # Relationship 3: Net Profit ↔ Net Profit Margin
        # -------------------------------------------------------------
        npm = ratio_map.get("net_profit_margin")
        if np is not None and npm is not None:
            rel = "aligned_profitability" if (np > 0 and npm > 0) or (np < 0 and npm < 0) else "neutral_or_divergent"
            comparisons.append({
                "metric_a": "net_profit",
                "metric_a_value": np,
                "metric_b": "net_profit_margin",
                "metric_b_value": npm,
                "relationship": rel,
                "evidence": ["findings.evidence.net_profit", "findings.ratios.net_profit_margin"],
            })

        # -------------------------------------------------------------
        # Relationship 4: Assets ↔ ROA
        # -------------------------------------------------------------
        assets = ev_map.get("assets")
        roa = ratio_map.get("return_on_assets")
        if assets is not None and roa is not None:
            rel = "positive_asset_efficiency" if roa > 0 else "negative_asset_efficiency"
            comparisons.append({
                "metric_a": "assets",
                "metric_a_value": assets,
                "metric_b": "return_on_assets",
                "metric_b_value": roa,
                "relationship": rel,
                "evidence": ["findings.evidence.assets", "findings.ratios.return_on_assets"],
            })

        # -------------------------------------------------------------
        # Relationship 5: Equity ↔ ROE
        # -------------------------------------------------------------
        equity = ev_map.get("equity")
        roe = ratio_map.get("return_on_equity")
        if equity is not None and roe is not None:
            rel = "positive_equity_return" if roe > 0 else "negative_equity_return"
            comparisons.append({
                "metric_a": "equity",
                "metric_a_value": equity,
                "metric_b": "return_on_equity",
                "metric_b_value": roe,
                "relationship": rel,
                "evidence": ["findings.evidence.equity", "findings.ratios.return_on_equity"],
            })

        # -------------------------------------------------------------
        # Relationship 6: Debt-to-Equity ↔ Debt Ratio
        # -------------------------------------------------------------
        dte = ratio_map.get("debt_to_equity")
        dr = ratio_map.get("debt_ratio")
        if dte is not None and dr is not None:
            rel = "consistent_leverage_profile"
            comparisons.append({
                "metric_a": "debt_to_equity",
                "metric_a_value": dte,
                "metric_b": "debt_ratio",
                "metric_b_value": dr,
                "relationship": rel,
                "evidence": ["findings.ratios.debt_to_equity", "findings.ratios.debt_ratio"],
            })

        # -------------------------------------------------------------
        # Relationship 7: Current Assets ↔ Current Ratio
        # -------------------------------------------------------------
        ca = ev_map.get("current_assets")
        cr = ratio_map.get("current_ratio")
        if ca is not None and cr is not None:
            rel = "strong_short_term_liquidity" if cr >= 1.0 else "constrained_short_term_liquidity"
            comparisons.append({
                "metric_a": "current_assets",
                "metric_a_value": ca,
                "metric_b": "current_ratio",
                "metric_b_value": cr,
                "relationship": rel,
                "evidence": ["findings.evidence.current_assets", "findings.ratios.current_ratio"],
            })

        # -------------------------------------------------------------
        # Relationship 8: Current Assets / Inventory ↔ Quick Ratio
        # -------------------------------------------------------------
        inv = ev_map.get("inventory")
        qr = ratio_map.get("quick_ratio")
        if inv is not None and qr is not None:
            rel = "strong_immediate_liquidity" if qr >= 1.0 else "inventory_reliant_liquidity"
            comparisons.append({
                "metric_a": "inventory",
                "metric_a_value": inv,
                "metric_b": "quick_ratio",
                "metric_b_value": qr,
                "relationship": rel,
                "evidence": ["findings.evidence.inventory", "findings.ratios.quick_ratio"],
            })

        # -------------------------------------------------------------
        # Relationship 9: YoY Revenue ↔ YoY Net Profit
        # -------------------------------------------------------------
        yoy_rev = yoy_map.get("revenue")
        yoy_np = yoy_map.get("net_profit")
        if yoy_rev and yoy_np:
            rev_dir = yoy_rev.get("direction")
            np_dir = yoy_np.get("direction")
            rev_pct = yoy_rev.get("percentage_change")
            np_pct = yoy_np.get("percentage_change")
            
            if rev_dir == "positive" and np_dir == "positive":
                rel = "synchronized_growth"
            elif rev_dir == "negative" and np_dir == "negative":
                rel = "synchronized_contraction"
            elif rev_dir == "positive" and np_dir == "negative":
                rel = "margin_compression_revenue_up_profit_down"
            elif rev_dir == "negative" and np_dir == "positive":
                rel = "margin_expansion_revenue_down_profit_up"
            else:
                rel = "mixed_directional_trends"

            comparisons.append({
                "metric_a": "yoy_revenue_percentage_change",
                "metric_a_value": rev_pct,
                "metric_b": "yoy_net_profit_percentage_change",
                "metric_b_value": np_pct,
                "relationship": rel,
                "evidence": ["findings.variances.revenue", "findings.variances.net_profit"],
            })

        # -------------------------------------------------------------
        # Relationship 10: YoY Assets ↔ YoY Equity
        # -------------------------------------------------------------
        yoy_ast = yoy_map.get("assets")
        yoy_eq = yoy_map.get("equity")
        if yoy_ast and yoy_eq:
            ast_pct = yoy_ast.get("percentage_change")
            eq_pct = yoy_eq.get("percentage_change")
            rel = "asset_equity_growth_correlation"
            comparisons.append({
                "metric_a": "yoy_assets_percentage_change",
                "metric_a_value": ast_pct,
                "metric_b": "yoy_equity_percentage_change",
                "metric_b_value": eq_pct,
                "relationship": rel,
                "evidence": ["findings.variances.assets", "findings.variances.equity"],
            })

        # -------------------------------------------------------------
        # Relationship 11: ML Anomaly ↔ High-Impact Ratios (e.g., Debt-to-Equity)
        # -------------------------------------------------------------
        anomalies = findings.get("anomalies", [])
        if anomalies and dte is not None:
            anom = anomalies[0]
            is_anom = anom.get("is_anomaly", False)
            score = anom.get("anomaly_score", 0.0)
            rel = "anomaly_associated_with_leverage" if is_anom else "normal_leverage_alignment"
            comparisons.append({
                "metric_a": "ml_anomaly_score",
                "metric_a_value": score,
                "metric_b": "debt_to_equity",
                "metric_b_value": dte,
                "relationship": rel,
                "evidence": ["findings.anomalies.isolation_forest", "findings.ratios.debt_to_equity"],
            })

        return comparisons
