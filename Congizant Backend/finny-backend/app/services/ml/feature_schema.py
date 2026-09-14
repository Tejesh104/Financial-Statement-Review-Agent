"""Authoritative ML feature schema for Finny Backend Anomaly Detection.

This module defines the single source of truth for:
- Canonical feature names
- Deterministic feature ordering
- Source mapping from dataset and Agent 1 ratio analyzer
- Preprocessing defaults and imputation rules
"""

from typing import List, Dict, Any

# Strict deterministic feature ordering used across training and inference
ML_FEATURE_NAMES: List[str] = [
    "current_ratio",
    "debt_to_equity",
    "roe",
    "roa",
    "net_profit_margin",
    "gross_profit_margin",
]

# Detailed metadata contract for each canonical feature
FEATURE_METADATA: Dict[str, Dict[str, Any]] = {
    "current_ratio": {
        "description": "Current Ratio (Current Assets / Current Liabilities)",
        "dataset_column": "Current Ratio",
        "agent1_path": "results.financial_ratios.ratios.liquidity.current_ratio.value",
        "category": "liquidity",
        "is_percentage": False,
        "default_imputation": 1.0,
    },
    "debt_to_equity": {
        "description": "Debt to Equity Ratio (Total Debt / Equity)",
        "dataset_column": "Debt/Equity Ratio",
        "agent1_path": "results.financial_ratios.ratios.leverage.debt_to_equity.value",
        "category": "leverage",
        "is_percentage": False,
        "default_imputation": 0.5,
    },
    "roe": {
        "description": "Return on Equity ((Net Profit / Equity) * 100)",
        "dataset_column": "ROE",
        "agent1_path": "results.financial_ratios.ratios.profitability.return_on_equity.value",
        "category": "profitability",
        "is_percentage": True,
        "default_imputation": 10.0,
    },
    "roa": {
        "description": "Return on Assets ((Net Profit / Total Assets) * 100)",
        "dataset_column": "ROA",
        "agent1_path": "results.financial_ratios.ratios.profitability.return_on_assets.value",
        "category": "profitability",
        "is_percentage": True,
        "default_imputation": 5.0,
    },
    "net_profit_margin": {
        "description": "Net Profit Margin ((Net Profit / Revenue) * 100)",
        "dataset_column": "Net Profit Margin",
        "agent1_path": "results.financial_ratios.ratios.profitability.net_profit_margin.value",
        "category": "profitability",
        "is_percentage": True,
        "default_imputation": 10.0,
    },
    "gross_profit_margin": {
        "description": "Gross Profit Margin ((Gross Profit / Revenue) * 100)",
        "dataset_column": "Gross Profit / Revenue * 100",
        "agent1_path": "results.financial_ratios.ratios.profitability.gross_profit_margin.value",
        "category": "profitability",
        "is_percentage": True,
        "default_imputation": 40.0,
    },
}

# Features present in Financial Statements.csv explicitly excluded from ML
EXCLUDED_DATASET_COLUMNS: Dict[str, str] = {
    "Company ": "Entity identifier; categorical leakage",
    "Category": "Categorical industry label; non-numeric",
    "Year": "Temporal marker, not a financial performance anomaly indicator",
    "Market Cap(in B USD)": "Market valuation metric outside financial statements; contains missing value",
    "Revenue": "Absolute dollar scale bias; large entities would be flagged solely for size",
    "Gross Profit": "Absolute dollar scale bias",
    "Net Income": "Absolute dollar scale bias",
    "Share Holder Equity": "Absolute dollar scale bias",
    "EBITDA": "Not standardized or extracted in Stage 1 schema",
    "Earning Per Share": "Per-share metric dependent on unmodeled outstanding shares count",
    "Free Cash Flow per Share": "Per-share cash metric outside Stage 1 extraction",
    "Cash Flow from Operating": "Cash flow statement line not in Stage 1 extraction",
    "Cash Flow from Investing": "Cash flow statement line not in Stage 1 extraction",
    "Cash Flow from Financial Activities": "Cash flow statement line not in Stage 1 extraction",
    "ROI": "Return on Investment is not defined in Agent 1 8 canonical ratios",
    "Return on Tangible Equity": "Not defined in Agent 1 8 canonical ratios",
    "Number of Employees": "Operational headcount outside financial statements",
    "Inflation Rate(in US)": "External macroeconomic indicator, not company statement data",
}


def get_feature_schema_dict() -> Dict[str, Any]:
    """Return JSON-serializable feature schema for export."""
    return {
        "feature_names": ML_FEATURE_NAMES,
        "feature_count": len(ML_FEATURE_NAMES),
        "features": FEATURE_METADATA,
        "excluded_columns": EXCLUDED_DATASET_COLUMNS,
    }
