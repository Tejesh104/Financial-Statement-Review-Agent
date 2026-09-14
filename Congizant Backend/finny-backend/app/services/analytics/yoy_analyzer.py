import re
import math
from typing import Dict, Any, Optional, Tuple, List


def _safe_float(val: Any) -> Optional[float]:
    """Safely parse input to a finite float or return None."""
    if val is None or str(val).strip() == "":
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (ValueError, TypeError):
        return None


class YoYAnalyzer:
    """Service for performing Year-Over-Year (YoY) financial analysis on normalized datasets."""

    CORE_FINANCIAL_FIELDS = [
        "revenue",
        "assets",
        "liabilities",
        "equity",
        "operating_income",
        "net_income",
        "cash",
        "inventory",
        "accounts_receivable",
        "accounts_payable",
        "expenses",
        "gross_profit",
        "current_assets",
        "current_liabilities",
    ]

    @staticmethod
    def parse_period_sort_key(period_str: Optional[str]) -> Tuple[int, int]:
        """Convert a period/fiscal year string into a sortable tuple of integers."""
        if not period_str:
            return (0, 0)

        clean = str(period_str).strip()

        fy_match = re.search(r"(?:FY\s*)?((?:19|20)\d{2})[-/](\d{2,4})", clean, re.IGNORECASE)
        if fy_match:
            start_yr = int(fy_match.group(1))
            end_part = fy_match.group(2)
            if len(end_part) == 2:
                end_yr = int(str(start_yr)[:2] + end_part)
            else:
                end_yr = int(end_part)
            return (start_yr, end_yr)

        # Check ISO date YYYY-MM-DD
        date_match = re.search(r"((?:19|20)\d{2})-(\d{2})-(\d{2})", clean)
        if date_match:
            return (int(date_match.group(1)), int(date_match.group(2)))

        # Check single 4-digit year e.g. 2024
        yr_match = re.search(r"\b((?:19|20)\d{2})\b", clean)
        if yr_match:
            yr = int(yr_match.group(1))
            return (yr, yr)

        return (0, 0)

    @staticmethod
    def calculate_field_yoy(previous: Optional[float], current: Optional[float]) -> Dict[str, Any]:
        """Calculate YoY metrics for a single financial field.
        
        Formulas:
            Absolute Change = Current Year - Previous Year
            Percentage Change = ((Current Year - Previous Year) / Previous Year) * 100
        
        Args:
            previous: Value from the earlier / previous period
            current: Value from the later / current period
            
        Returns:
            Dict[str, Any] matching the FieldYoYResult schema.
        """
        # 1. Missing / invalid value handling
        previous = _safe_float(previous)
        current = _safe_float(current)

        if previous is None and current is None:
            return {
                "previous": None,
                "current": None,
                "absolute_change": None,
                "percentage_change": None,
                "direction": None,
                "status": "INCOMPLETE",
                "reason": "Both previous and current period values are missing",
            }
        if previous is None:
            return {
                "previous": None,
                "current": current,
                "absolute_change": None,
                "percentage_change": None,
                "direction": None,
                "status": "INCOMPLETE",
                "reason": "Previous period value is missing",
            }
        if current is None:
            return {
                "previous": previous,
                "current": None,
                "absolute_change": None,
                "percentage_change": None,
                "direction": None,
                "status": "INCOMPLETE",
                "reason": "Current period value is missing",
            }

        # 2. Numerical calculations
        absolute_change = current - previous

        # Determine mathematical direction of change
        if absolute_change > 0:
            direction = "positive"
        elif absolute_change < 0:
            direction = "negative"
        else:
            direction = "unchanged"

        # 3. Handle zero previous value
        if previous == 0:
            return {
                "previous": previous,
                "current": current,
                "absolute_change": absolute_change,
                "percentage_change": None,
                "direction": direction,
                "status": "COMPLETED",
                "reason": "Percentage change cannot be calculated because previous value is zero.",
            }

        # 4. Standard percentage change
        percentage_change = (absolute_change / abs(previous)) * 100.0

        return {
            "previous": previous,
            "current": current,
            "absolute_change": absolute_change,
            "percentage_change": percentage_change,
            "direction": direction,
            "status": "COMPLETED",
            "reason": None,
        }

    @classmethod
    def analyze_periods(
        cls,
        previous_period: Optional[str],
        current_period: Optional[str],
        previous_metrics: Dict[str, Any],
        current_metrics: Dict[str, Any],
        fields_to_analyze: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Perform full YoY analysis across multiple financial fields between two periods."""
        if not previous_period or not current_period or previous_metrics is None or current_metrics is None:
            return {
                "status": "INSUFFICIENT_DATA",
                "periods": None,
                "financial_data": {},
                "warnings": ["At least two financial periods are required for YoY analysis"],
                "reason": "At least two financial periods are required for YoY analysis",
            }

        # Check if periods need chronological ordering
        key_prev = cls.parse_period_sort_key(previous_period)
        key_curr = cls.parse_period_sort_key(current_period)
        if key_prev > key_curr and key_prev != (0, 0) and key_curr != (0, 0):
            previous_period, current_period = current_period, previous_period
            previous_metrics, current_metrics = current_metrics, previous_metrics

        # If fields_to_analyze is explicitly provided, use it.
        # Otherwise, dynamically evaluate fields present in either dictionary.
        # Ensure canonical core fields (revenue, assets, liabilities, equity) are always tracked
        # if the document has any primary data, so that missing balance sheet components are marked INCOMPLETE.
        if fields_to_analyze:
            active_fields = fields_to_analyze
        else:
            active_fields = [f for f in cls.CORE_FINANCIAL_FIELDS if f in previous_metrics or f in current_metrics]

        financial_results: Dict[str, Any] = {}
        warnings: List[str] = []
        has_completed = False
        has_incomplete = False

        for field in active_fields:
            p_val = previous_metrics.get(field)
            c_val = current_metrics.get(field)

            p_num = _safe_float(p_val)
            c_num = _safe_float(c_val)

            res = cls.calculate_field_yoy(p_num, c_num)
            financial_results[field] = res

            if res["status"] == "COMPLETED":
                has_completed = True
                if res.get("reason"):
                    warnings.append(f"{field}: {res['reason']}")
            else:
                has_incomplete = True
                if res.get("reason"):
                    warnings.append(f"{field}: {res['reason']}")

        overall_status = "COMPLETED" if (has_completed and not has_incomplete) else ("INCOMPLETE" if has_completed else "INSUFFICIENT_DATA")

        return {
            "status": overall_status,
            "periods": {
                "previous": previous_period,
                "current": current_period,
            },
            "financial_data": financial_results,
            "warnings": warnings,
            "reason": None if overall_status == "COMPLETED" else "One or more financial fields are incomplete or missing",
        }
