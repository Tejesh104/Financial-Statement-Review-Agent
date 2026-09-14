"""Deterministic investigation service for Agent 1 Findings.

Investigates:
  1. Mathematical validation (valid vs invalid vs incomplete)
  2. YoY financial variances (significant shifts, positive/negative/unchanged)
  3. ML statistical anomalies (preserving unsupervised anomaly detection semantics)
  4. Financial ratios (completed vs incomplete vs undefined with exact reasons)
  5. Evidence availability
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class InvestigationService:
    """Investigates verified findings deterministically without inventing facts."""

    @classmethod
    def investigate(cls, findings: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Run investigations across all finding sections.

        Args:
            findings: Dict with keys 'validations', 'variances', 'anomalies', 'ratios', 'evidence'.

        Returns:
            List of investigation item dicts.
        """
        investigations: List[Dict[str, Any]] = []

        # -------------------------------------------------------------
        # 1. Investigate Math Validations
        # -------------------------------------------------------------
        validations = findings.get("validations", [])
        if not validations:
            investigations.append({
                "category": "VALIDATION",
                "target": "balance_sheet_equation",
                "status": "INCOMPLETE",
                "description": "Mathematical validation data is absent for this document.",
                "evidence": ["findings.validations"],
                "reason": "Math validation has not been performed.",
            })
        else:
            for val in validations:
                v_type = val.get("type", "BALANCE_SHEET_VALIDATION")
                v_status = val.get("status", "INCOMPLETE")
                diff = val.get("difference")
                tol = val.get("tolerance")
                reason = val.get("reason")

                if v_status == "VALID":
                    diff_str = f"{diff:.2f}" if diff is not None else "0.00"
                    investigations.append({
                        "category": "VALIDATION",
                        "target": v_type,
                        "status": "VALID",
                        "description": f"Balance sheet equation holds (Assets = Liabilities + Equity) within tolerance {tol} (difference: {diff_str}).",
                        "evidence": ["findings.validations.balance_sheet_check"],
                        "reason": None,
                    })
                elif v_status == "INVALID":
                    diff_str = f"{diff:.2f}" if diff is not None else "N/A"
                    investigations.append({
                        "category": "VALIDATION",
                        "target": v_type,
                        "status": "INVALID",
                        "description": f"Balance sheet equation does not balance. Imbalance difference: {diff_str}.",
                        "evidence": ["findings.validations.balance_sheet_check"],
                        "reason": reason or f"Difference {diff_str} exceeds tolerance {tol}.",
                    })
                else:
                    investigations.append({
                        "category": "VALIDATION",
                        "target": v_type,
                        "status": "INCOMPLETE",
                        "description": "Balance sheet equation validation could not be completed due to missing values.",
                        "evidence": ["findings.validations.balance_sheet_check"],
                        "reason": reason or "Missing assets, liabilities, or equity.",
                    })

        # -------------------------------------------------------------
        # 2. Investigate YoY Variances
        # -------------------------------------------------------------
        variances = findings.get("variances", [])
        if not variances:
            investigations.append({
                "category": "YOY",
                "target": "periods_analysis",
                "status": "INSUFFICIENT_DATA",
                "description": "Year-over-Year variance analysis could not be conducted because fewer than two financial periods are available.",
                "evidence": ["findings.variances"],
                "reason": "At least two distinct financial periods are required for YoY comparison.",
            })
        else:
            for var in variances:
                field = var.get("field", "unknown_metric")
                status = var.get("status", "COMPLETED")
                direction = var.get("direction")
                pct_change = var.get("percentage_change")
                abs_change = var.get("absolute_change")
                cur_val = var.get("current_value")
                prev_val = var.get("previous_value")
                cur_period = var.get("current_period", "Current")
                prev_period = var.get("previous_period", "Previous")
                reason = var.get("reason")

                ev_path = f"findings.variances.{field}"

                if status == "COMPLETED":
                    pct_str = f"{pct_change:+.2f}%" if pct_change is not None else "0.00%"
                    abs_str = f"{abs_change:+,.2f}" if abs_change is not None else "0.00"
                    
                    if direction == "positive":
                        desc = f"{field.replace('_', ' ').title()} increased by {abs_str} ({pct_str}) from {prev_period} ({prev_val:,.2f}) to {cur_period} ({cur_val:,.2f})."
                    elif direction == "negative":
                        desc = f"{field.replace('_', ' ').title()} decreased by {abs_str} ({pct_str}) from {prev_period} ({prev_val:,.2f}) to {cur_period} ({cur_val:,.2f})."
                    else:
                        desc = f"{field.replace('_', ' ').title()} remained unchanged between {prev_period} and {cur_period} at {cur_val:,.2f}."

                    investigations.append({
                        "category": "YOY",
                        "target": field,
                        "status": "COMPLETED",
                        "description": desc,
                        "evidence": [ev_path],
                        "reason": None,
                    })
                else:
                    investigations.append({
                        "category": "YOY",
                        "target": field,
                        "status": status,
                        "description": f"YoY analysis for {field} is incomplete or undefined.",
                        "evidence": [ev_path],
                        "reason": reason or "Previous period value zero or missing data.",
                    })

        # -------------------------------------------------------------
        # 3. Investigate ML Anomalies
        # -------------------------------------------------------------
        anomalies = findings.get("anomalies", [])
        if not anomalies:
            investigations.append({
                "category": "ML_ANOMALY",
                "target": "isolation_forest",
                "status": "INCOMPLETE",
                "description": "ML anomaly detection output was not found in findings.",
                "evidence": ["findings.anomalies"],
                "reason": "Anomaly detection inference not completed.",
            })
        else:
            for anom in anomalies:
                classification = anom.get("classification", "NORMAL")
                is_anomaly = anom.get("is_anomaly", False)
                score = anom.get("anomaly_score", 0.0)
                model_type = anom.get("model_type", "IsolationForest")
                reason = anom.get("reason")

                ev_path = "findings.anomalies.isolation_forest"

                if is_anomaly or classification == "ANOMALY":
                    desc = (
                        f"Statistical anomaly flagged by {model_type} with anomaly score {score:.4f} (< 0 threshold). "
                        "Indicates multi-ratio feature combination is statistically unusual relative to the training distribution."
                    )
                    investigations.append({
                        "category": "ML_ANOMALY",
                        "target": "statistical_anomaly",
                        "status": "ANOMALY",
                        "description": desc,
                        "evidence": [ev_path],
                        "reason": reason or "Multi-metric ratio vector deviates significantly from training baseline.",
                    })
                else:
                    desc = (
                        f"Statistical normality confirmed by {model_type} with anomaly score {score:.4f} (>= 0 threshold). "
                        "Ratio feature profile conforms to expected patterns in the training distribution."
                    )
                    investigations.append({
                        "category": "ML_ANOMALY",
                        "target": "statistical_normality",
                        "status": "NORMAL",
                        "description": desc,
                        "evidence": [ev_path],
                        "reason": None,
                    })

        # -------------------------------------------------------------
        # 4. Investigate Financial Ratios
        # -------------------------------------------------------------
        ratios = findings.get("ratios", [])
        if not ratios:
            investigations.append({
                "category": "RATIO",
                "target": "financial_ratios",
                "status": "INCOMPLETE",
                "description": "Financial ratio calculations are absent in findings.",
                "evidence": ["findings.ratios"],
                "reason": "Ratio analysis has not been executed.",
            })
        else:
            for r in ratios:
                name = r.get("name", "unknown_ratio")
                category = r.get("category", "general")
                status = r.get("status", "INCOMPLETE")
                val = r.get("value")
                reason = r.get("reason")
                ev_path = f"findings.ratios.{name}"

                readable_name = name.replace("_", " ").title()

                if status == "COMPLETED" and val is not None:
                    # Note percentage margins vs standard ratios
                    if "margin" in name or "return" in name:
                        val_str = f"{val:.2f}%"
                    else:
                        val_str = f"{val:.2f}"
                    desc = f"{readable_name} ({category}) is {val_str}."
                    investigations.append({
                        "category": "RATIO",
                        "target": name,
                        "status": "COMPLETED",
                        "description": desc,
                        "evidence": [ev_path],
                        "reason": None,
                    })
                elif status == "UNDEFINED":
                    desc = f"{readable_name} ({category}) is undefined."
                    investigations.append({
                        "category": "RATIO",
                        "target": name,
                        "status": "UNDEFINED",
                        "description": desc,
                        "evidence": [ev_path],
                        "reason": reason or "Zero denominator encountered in ratio calculation.",
                    })
                else:
                    desc = f"{readable_name} ({category}) could not be calculated due to missing inputs."
                    investigations.append({
                        "category": "RATIO",
                        "target": name,
                        "status": "INCOMPLETE",
                        "description": desc,
                        "evidence": [ev_path],
                        "reason": reason or "Required financial metric missing from statement.",
                    })

        # -------------------------------------------------------------
        # 5. Check Evidence Availability
        # -------------------------------------------------------------
        evidence = findings.get("evidence", [])
        missing_ev = [e.get("field") for e in evidence if not e.get("is_available", False)]
        if missing_ev:
            investigations.append({
                "category": "EVIDENCE",
                "target": "missing_line_items",
                "status": "PARTIAL",
                "description": f"The following line items are missing from the normalized statement: {', '.join(missing_ev)}.",
                "evidence": [f"findings.evidence.{f}" for f in missing_ev],
                "reason": "Fields not reported in source document.",
            })

        return investigations
