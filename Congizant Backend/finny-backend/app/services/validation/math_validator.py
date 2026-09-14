import math
from typing import Optional, Dict, Any

# Standard floating point / rounding tolerance for currency calculations
# Rationale: Financial metrics represented as IEEE 754 floats can incur minor
# precision artifacts (e.g., 0.0000001). A tolerance of 0.01 currency units
# accommodates rounding while strictly flagging genuine financial discrepancies.
DEFAULT_TOLERANCE: float = 0.01


def _safe_float(val: Any) -> Optional[float]:
    """Safely convert any input value to a finite float or return None."""
    if val is None or str(val).strip() == "":
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (ValueError, TypeError):
        return None


class MathValidator:
    """Mathematical validation service checking fundamental accounting identities."""

    @staticmethod
    def validate_balance_sheet(
        assets: Optional[float],
        liabilities: Optional[float],
        equity: Optional[float],
        tolerance: float = DEFAULT_TOLERANCE
    ) -> Dict[str, Any]:
        """Validate the fundamental balance sheet equation: Assets = Liabilities + Equity.
        
        Args:
            assets: Total assets value (or None if missing)
            liabilities: Total liabilities value (or None if missing)
            equity: Total shareholders'/owners' equity value (or None if missing)
            tolerance: Maximum allowable difference between Assets and (Liabilities + Equity)
            
        Returns:
            Dict[str, Any]: Structured validation result with status VALID, INVALID, or INCOMPLETE.
        """
        # Sanitize numeric inputs against malformed strings, NaN, and infinity
        clean_assets = _safe_float(assets)
        clean_liabilities = _safe_float(liabilities)
        clean_equity = _safe_float(equity)

        # 1. Identify any missing required fields
        missing_fields = []
        if clean_assets is None:
            missing_fields.append("assets")
        if clean_liabilities is None:
            missing_fields.append("liabilities")
        if clean_equity is None:
            missing_fields.append("equity")

        if missing_fields:
            missing_str = ", ".join(missing_fields)
            return {
                "assets": clean_assets,
                "liabilities": clean_liabilities,
                "equity": clean_equity,
                "liabilities_plus_equity": None,
                "difference": None,
                "tolerance": tolerance,
                "is_valid": None,
                "status": "INCOMPLETE",
                "reason": f"Missing {missing_str} value"
            }

        # 2. Perform the accounting equation check
        # Note: 0 and negative values are mathematically valid and computed algebraically
        liabilities_plus_equity = clean_liabilities + clean_equity
        difference = clean_assets - liabilities_plus_equity
        is_valid = abs(difference) <= tolerance

        status = "VALID" if is_valid else "INVALID"
        reason = None
        if not is_valid:
            reason = (
                f"Balance sheet mismatch: Assets ({clean_assets:,.2f}) != Liabilities + Equity "
                f"({liabilities_plus_equity:,.2f}) with difference of {difference:,.2f} "
                f"(tolerance: {tolerance})"
            )

        return {
            "assets": clean_assets,
            "liabilities": clean_liabilities,
            "equity": clean_equity,
            "liabilities_plus_equity": liabilities_plus_equity,
            "difference": difference,
            "tolerance": tolerance,
            "is_valid": is_valid,
            "status": status,
            "reason": reason
        }
