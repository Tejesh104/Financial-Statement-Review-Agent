"""Feature builder for Isolation Forest ML model.

Extracts, computes, validates, and aligns feature vectors for both:
1. Training (from Financial Statements.csv)
2. Inference (from Agent 1 output dictionary or normalized financial data)
"""

import math
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple
import pandas as pd

from app.services.ml.feature_schema import ML_FEATURE_NAMES, FEATURE_METADATA


def _safe_numeric(val: Any) -> Optional[float]:
    """Parse input to float, returning None for missing, NaN, or Inf."""
    if val is None or str(val).strip() == "":
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (ValueError, TypeError):
        return None


class FeatureBuilder:
    """Builder for canonical ML feature vectors."""

    @classmethod
    def build_features_from_csv(
        cls,
        csv_path: Union[str, Path],
        handle_missing: bool = True
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Extract canonical features from the Financial Statements.csv training dataset.

        Returns:
            Tuple of (features_df, metadata_df) where features_df columns strictly match ML_FEATURE_NAMES.
        """
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"Training dataset not found at {path}")

        df = pd.read_csv(path)

        # Validate expected base columns exist in dataset
        expected_cols = ["Current Ratio", "Debt/Equity Ratio", "ROE", "ROA", "Net Profit Margin", "Gross Profit", "Revenue"]
        missing = [col for col in expected_cols if col not in df.columns]
        if missing:
            raise ValueError(f"Dataset missing required columns for feature building: {missing}")

        features_df = pd.DataFrame(index=df.index)

        # 1. Direct mappings
        features_df["current_ratio"] = df["Current Ratio"].apply(_safe_numeric)
        features_df["debt_to_equity"] = df["Debt/Equity Ratio"].apply(_safe_numeric)
        features_df["roe"] = df["ROE"].apply(_safe_numeric)
        features_df["roa"] = df["ROA"].apply(_safe_numeric)
        features_df["net_profit_margin"] = df["Net Profit Margin"].apply(_safe_numeric)

        # 2. Derived gross_profit_margin = (Gross Profit / Revenue) * 100
        def calc_gpm(row):
            gp = _safe_numeric(row["Gross Profit"])
            rev = _safe_numeric(row["Revenue"])
            if gp is None or rev is None or rev == 0:
                return None
            return round((gp / rev) * 100.0, 4)

        features_df["gross_profit_margin"] = df.apply(calc_gpm, axis=1)

        # 3. Handle missing values deterministically if requested
        if handle_missing:
            for feat in ML_FEATURE_NAMES:
                default_val = FEATURE_METADATA[feat]["default_imputation"]
                # If any missing in training set, fill with median or default
                if features_df[feat].isnull().any():
                    median_val = features_df[feat].median()
                    fill_val = median_val if not pd.isna(median_val) else default_val
                    features_df[feat] = features_df[feat].fillna(fill_val)

        # Strict ordering
        features_df = features_df[ML_FEATURE_NAMES]

        # Metadata frame for tracking entities without leaking into features
        meta_cols = [c for c in ["Company ", "Year", "Category"] if c in df.columns]
        metadata_df = df[meta_cols].copy()
        if "Company " in metadata_df.columns:
            metadata_df.rename(columns={"Company ": "Company"}, inplace=True)

        return features_df, metadata_df

    @classmethod
    def extract_features_from_agent1_dict(
        cls,
        agent1_data: Dict[str, Any],
        handle_missing: bool = True
    ) -> List[float]:
        """Extract a single feature vector aligned with ML_FEATURE_NAMES from Agent 1 output dict.

        Args:
            agent1_data: The JSON dictionary produced by Agent 1 Result Builder.
            handle_missing: If True, uses canonical defaults for missing or undefined ratios.

        Returns:
            List of float values in the exact order of ML_FEATURE_NAMES.
        """
        ratios_block = (
            agent1_data.get("results", {})
            .get("financial_ratios", {})
            .get("ratios", {})
        )

        liquidity = ratios_block.get("liquidity", {})
        leverage = ratios_block.get("leverage", {})
        profitability = ratios_block.get("profitability", {})

        raw_values: Dict[str, Optional[float]] = {
            "current_ratio": _safe_numeric(liquidity.get("current_ratio", {}).get("value")),
            "debt_to_equity": _safe_numeric(leverage.get("debt_to_equity", {}).get("value")),
            "roe": _safe_numeric(profitability.get("return_on_equity", {}).get("value")),
            "roa": _safe_numeric(profitability.get("return_on_assets", {}).get("value")),
            "net_profit_margin": _safe_numeric(profitability.get("net_profit_margin", {}).get("value")),
            "gross_profit_margin": _safe_numeric(profitability.get("gross_profit_margin", {}).get("value")),
        }

        vector: List[float] = []
        for feat in ML_FEATURE_NAMES:
            val = raw_values.get(feat)
            if val is None:
                if handle_missing:
                    val = float(FEATURE_METADATA[feat]["default_imputation"])
                else:
                    raise ValueError(f"Feature '{feat}' is missing from input and handle_missing=False")
            vector.append(float(val))

        return vector
