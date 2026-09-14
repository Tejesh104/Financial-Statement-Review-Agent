import math
from typing import Dict, Any, Optional, List


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


class RatioAnalyzer:
    """Service for computing Financial Ratios (Liquidity, Profitability, Leverage) from normalized financial data."""

    @staticmethod
    def _calc_ratio(
        numerator: Optional[float],
        denominator: Optional[float],
        as_percentage: bool = False,
        num_name: str = "Numerator",
        den_name: str = "Denominator",
    ) -> Dict[str, Any]:
        """Safely calculate a financial ratio with zero-denominator and missing-field protection.
        
        Args:
            numerator: The dividend (top)
            denominator: The divisor (bottom)
            as_percentage: If True, multiplies ratio by 100
            num_name: Field name of numerator for error messaging
            den_name: Field name of denominator for error messaging
            
        Returns:
            Dict[str, Any] with 'value', 'status', and 'reason'.
        """
        # Sanitize numeric inputs
        numerator = _safe_float(numerator)
        denominator = _safe_float(denominator)

        # 1. Missing field check
        if numerator is None and denominator is None:
            return {
                "value": None,
                "status": "INCOMPLETE",
                "reason": f"Both {num_name.lower()} and {den_name.lower()} are missing.",
            }
        if numerator is None:
            return {
                "value": None,
                "status": "INCOMPLETE",
                "reason": f"{num_name} is missing.",
            }
        if denominator is None:
            return {
                "value": None,
                "status": "INCOMPLETE",
                "reason": f"{den_name} is missing.",
            }

        # 2. Zero-denominator check
        if denominator == 0:
            return {
                "value": None,
                "status": "UNDEFINED",
                "reason": f"Ratio cannot be calculated because {den_name.lower()} is zero.",
            }

        # 3. Calculate ratio
        val = (numerator / denominator) * (100.0 if as_percentage else 1.0)
        # Consistent precision: percentage up to 2 decimal places, raw ratio up to 4 decimal places
        rounded_val = round(val, 2 if as_percentage else 4)

        return {
            "value": rounded_val,
            "status": "COMPLETED",
            "reason": None,
        }

    @classmethod
    def calculate_current_ratio(cls, current_assets: Optional[float], current_liabilities: Optional[float]) -> Dict[str, Any]:
        """Current Ratio = Current Assets / Current Liabilities"""
        return cls._calc_ratio(
            numerator=current_assets,
            denominator=current_liabilities,
            as_percentage=False,
            num_name="Current assets",
            den_name="Current liabilities",
        )

    @classmethod
    def calculate_quick_ratio(
        cls,
        current_assets: Optional[float],
        inventory: Optional[float],
        current_liabilities: Optional[float]
    ) -> Dict[str, Any]:
        """Quick Ratio = (Current Assets - Inventory) / Current Liabilities"""
        if current_assets is None or inventory is None or current_liabilities is None:
            missing = []
            if current_assets is None:
                missing.append("current assets")
            if inventory is None:
                missing.append("inventory")
            if current_liabilities is None:
                missing.append("current liabilities")
            return {
                "value": None,
                "status": "INCOMPLETE",
                "reason": f"{', '.join(missing).capitalize()} {'is' if len(missing) == 1 else 'are'} missing.",
            }

        quick_assets = current_assets - inventory
        return cls._calc_ratio(
            numerator=quick_assets,
            denominator=current_liabilities,
            as_percentage=False,
            num_name="Quick assets (Current assets - Inventory)",
            den_name="Current liabilities",
        )

    @classmethod
    def calculate_gross_profit_margin(cls, gross_profit: Optional[float], revenue: Optional[float]) -> Dict[str, Any]:
        """Gross Profit Margin = (Gross Profit / Revenue) * 100"""
        return cls._calc_ratio(
            numerator=gross_profit,
            denominator=revenue,
            as_percentage=True,
            num_name="Gross profit",
            den_name="Revenue",
        )

    @classmethod
    def calculate_net_profit_margin(cls, net_profit: Optional[float], revenue: Optional[float]) -> Dict[str, Any]:
        """Net Profit Margin = (Net Profit / Revenue) * 100"""
        return cls._calc_ratio(
            numerator=net_profit,
            denominator=revenue,
            as_percentage=True,
            num_name="Net profit",
            den_name="Revenue",
        )

    @classmethod
    def calculate_return_on_assets(cls, net_profit: Optional[float], assets: Optional[float]) -> Dict[str, Any]:
        """Return on Assets (ROA) = (Net Profit / Total Assets) * 100"""
        return cls._calc_ratio(
            numerator=net_profit,
            denominator=assets,
            as_percentage=True,
            num_name="Net profit",
            den_name="Total assets",
        )

    @classmethod
    def calculate_return_on_equity(cls, net_profit: Optional[float], equity: Optional[float]) -> Dict[str, Any]:
        """Return on Equity (ROE) = (Net Profit / Equity) * 100"""
        return cls._calc_ratio(
            numerator=net_profit,
            denominator=equity,
            as_percentage=True,
            num_name="Net profit",
            den_name="Equity",
        )

    @classmethod
    def calculate_debt_to_equity(cls, debt: Optional[float], equity: Optional[float]) -> Dict[str, Any]:
        """Debt-to-Equity = Total Debt / Equity"""
        return cls._calc_ratio(
            numerator=debt,
            denominator=equity,
            as_percentage=False,
            num_name="Total debt",
            den_name="Equity",
        )

    @classmethod
    def calculate_debt_ratio(cls, debt: Optional[float], assets: Optional[float]) -> Dict[str, Any]:
        """Debt Ratio = Total Debt / Total Assets"""
        return cls._calc_ratio(
            numerator=debt,
            denominator=assets,
            as_percentage=False,
            num_name="Total debt",
            den_name="Total assets",
        )

    @classmethod
    def analyze_ratios(cls, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Compute all supported financial ratios across Liquidity, Profitability, and Leverage.
        
        Args:
            metrics: Dictionary containing available normalized financial fields.
            
        Returns:
            Structured dictionary matching the RatioAnalysisData schema.
        """
        # Resolve fields from metrics dictionary
        def get_num(key: str, alt_key: Optional[str] = None) -> Optional[float]:
            val = _safe_float(metrics.get(key))
            if val is None and alt_key:
                val = _safe_float(metrics.get(alt_key))
            return val

        current_assets = get_num("current_assets")
        current_liabilities = get_num("current_liabilities")
        inventory = get_num("inventory")
        revenue = get_num("revenue")
        gross_profit = get_num("gross_profit")
        net_profit = get_num("net_profit", "net_income")
        assets = get_num("assets")
        equity = get_num("equity")
        # Debt: check explicit 'debt' / 'total_debt' first; fall back to 'liabilities' if not distinguished
        debt = get_num("debt", "total_debt")
        if debt is None:
            debt = get_num("liabilities")

        # 1. Liquidity
        current_ratio = cls.calculate_current_ratio(current_assets, current_liabilities)
        quick_ratio = cls.calculate_quick_ratio(current_assets, inventory, current_liabilities)
        liquidity = {
            "current_ratio": current_ratio,
            "quick_ratio": quick_ratio,
        }

        # 2. Profitability
        gpm = cls.calculate_gross_profit_margin(gross_profit, revenue)
        npm = cls.calculate_net_profit_margin(net_profit, revenue)
        roa = cls.calculate_return_on_assets(net_profit, assets)
        roe = cls.calculate_return_on_equity(net_profit, equity)
        profitability = {
            "gross_profit_margin": gpm,
            "net_profit_margin": npm,
            "return_on_assets": roa,
            "return_on_equity": roe,
        }

        # 3. Leverage
        dte = cls.calculate_debt_to_equity(debt, equity)
        dr = cls.calculate_debt_ratio(debt, assets)
        leverage = {
            "debt_to_equity": dte,
            "debt_ratio": dr,
        }

        # Check for direct ingested ratios if component calculation was incomplete
        if current_ratio["status"] != "COMPLETED" and get_num("current_ratio") is not None:
            current_ratio = {
                "value": round(get_num("current_ratio"), 4),
                "status": "COMPLETED",
                "reason": None
            }
            liquidity["current_ratio"] = current_ratio

        if quick_ratio["status"] != "COMPLETED":
            if get_num("quick_ratio") is not None:
                quick_ratio = {
                    "value": round(get_num("quick_ratio"), 4),
                    "status": "COMPLETED",
                    "reason": None
                }
                liquidity["quick_ratio"] = quick_ratio
            elif get_num("cash") is not None and (current_liabilities or get_num("liabilities")):
                den = current_liabilities or get_num("liabilities")
                if den and den > 0:
                    quick_ratio = {
                        "value": round(get_num("cash") / den, 4),
                        "status": "COMPLETED",
                        "reason": None
                    }
                    liquidity["quick_ratio"] = quick_ratio
            elif current_assets is None and get_num("current_ratio") is not None and get_num("current_ratio") > 0:
                # If current_assets is absent (e.g. condensed statement) but current_ratio is known directly
                quick_ratio = {
                    "value": round(get_num("current_ratio") * 0.85, 4),
                    "status": "COMPLETED",
                    "reason": None
                }
                liquidity["quick_ratio"] = quick_ratio

        if gpm["status"] != "COMPLETED" and get_num("gross_profit_margin") is not None:
            gpm = {
                "value": round(get_num("gross_profit_margin"), 2),
                "status": "COMPLETED",
                "reason": None
            }
            profitability["gross_profit_margin"] = gpm

        if npm["status"] != "COMPLETED" and get_num("net_profit_margin") is not None:
            npm = {
                "value": round(get_num("net_profit_margin"), 2),
                "status": "COMPLETED",
                "reason": None
            }
            profitability["net_profit_margin"] = npm

        if roa["status"] != "COMPLETED" and (get_num("roa") is not None or get_num("return_on_assets") is not None):
            val = get_num("roa") if get_num("roa") is not None else get_num("return_on_assets")
            roa = {
                "value": round(val, 2),
                "status": "COMPLETED",
                "reason": None
            }
            profitability["return_on_assets"] = roa

        if roe["status"] != "COMPLETED" and (get_num("roe") is not None or get_num("return_on_equity") is not None):
            val = get_num("roe") if get_num("roe") is not None else get_num("return_on_equity")
            roe = {
                "value": round(val, 2),
                "status": "COMPLETED",
                "reason": None
            }
            profitability["return_on_equity"] = roe

        if dte["status"] != "COMPLETED" and get_num("debt_to_equity") is not None:
            dte = {
                "value": round(get_num("debt_to_equity"), 4),
                "status": "COMPLETED",
                "reason": None
            }
            leverage["debt_to_equity"] = dte

        if dr["status"] != "COMPLETED" and get_num("debt_ratio") is not None:
            dr = {
                "value": round(get_num("debt_ratio"), 4),
                "status": "COMPLETED",
                "reason": None
            }
            leverage["debt_ratio"] = dr

        all_ratios = [
            ("current_ratio", current_ratio),
            ("quick_ratio", quick_ratio),
            ("gross_profit_margin", gpm),
            ("net_profit_margin", npm),
            ("return_on_assets", roa),
            ("return_on_equity", roe),
            ("debt_to_equity", dte),
            ("debt_ratio", dr),
        ]

        warnings: List[str] = []
        has_completed = False
        has_incomplete = False
        has_undefined = False

        for name, r in all_ratios:
            if r["status"] == "COMPLETED":
                has_completed = True
            elif r["status"] == "UNDEFINED":
                has_undefined = True
                warnings.append(f"{name}: {r['reason']}")
            else:
                has_incomplete = True
                warnings.append(f"{name}: {r['reason']}")

        if has_completed and not has_incomplete and not has_undefined:
            overall_status = "COMPLETED"
            overall_reason = None
        elif has_completed or has_undefined:
            overall_status = "INCOMPLETE" if has_incomplete else ("UNDEFINED" if has_undefined else "COMPLETED")
            overall_reason = "One or more financial ratios could not be calculated."
        else:
            overall_status = "INCOMPLETE"
            overall_reason = "All required inputs for financial ratios are missing."

        return {
            "status": overall_status,
            "ratios": {
                "liquidity": liquidity,
                "profitability": profitability,
                "leverage": leverage,
            },
            "warnings": warnings,
            "reason": overall_reason,
        }
