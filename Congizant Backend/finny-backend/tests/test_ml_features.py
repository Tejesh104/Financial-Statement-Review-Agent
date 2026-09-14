"""Tests for ML feature schema, engineering, and extraction."""

import pytest
import pandas as pd
from pathlib import Path

from app.services.ml.feature_schema import (
    ML_FEATURE_NAMES,
    FEATURE_METADATA,
    EXCLUDED_DATASET_COLUMNS,
    get_feature_schema_dict,
)
from app.services.ml.feature_builder import FeatureBuilder, _safe_numeric


def test_feature_schema_definition():
    """Verify feature schema is non-empty, list of strings, and deterministic."""
    assert isinstance(ML_FEATURE_NAMES, list)
    assert len(ML_FEATURE_NAMES) == 6
    assert ML_FEATURE_NAMES == [
        "current_ratio",
        "debt_to_equity",
        "roe",
        "roa",
        "net_profit_margin",
        "gross_profit_margin",
    ]


def test_feature_metadata_integrity():
    """Verify each feature has complete metadata."""
    for feat in ML_FEATURE_NAMES:
        assert feat in FEATURE_METADATA
        meta = FEATURE_METADATA[feat]
        assert "description" in meta
        assert "dataset_column" in meta
        assert "agent1_path" in meta
        assert "category" in meta
        assert "is_percentage" in meta
        assert "default_imputation" in meta


def test_excluded_columns_documentation():
    """Verify excluded dataset columns are documented with reasons."""
    assert "Company " in EXCLUDED_DATASET_COLUMNS
    assert "Year" in EXCLUDED_DATASET_COLUMNS
    assert "Market Cap(in B USD)" in EXCLUDED_DATASET_COLUMNS
    assert "Revenue" in EXCLUDED_DATASET_COLUMNS
    assert "EBITDA" in EXCLUDED_DATASET_COLUMNS
    for col, reason in EXCLUDED_DATASET_COLUMNS.items():
        assert len(reason) > 5


def test_get_feature_schema_dict():
    """Verify JSON schema dictionary output."""
    schema_dict = get_feature_schema_dict()
    assert schema_dict["feature_count"] == 6
    assert schema_dict["feature_names"] == ML_FEATURE_NAMES
    assert "features" in schema_dict
    assert "excluded_columns" in schema_dict


def test_safe_numeric_helper():
    """Verify numeric parsing and sanitation."""
    assert _safe_numeric(12.34) == 12.34
    assert _safe_numeric("56.78") == 56.78
    assert _safe_numeric("  -99.1  ") == -99.1
    assert _safe_numeric(None) is None
    assert _safe_numeric("") is None
    assert _safe_numeric("invalid") is None
    assert _safe_numeric(float("nan")) is None
    assert _safe_numeric(float("inf")) is None


def test_feature_builder_from_csv(tmp_path):
    """Verify feature extraction and engineering from CSV."""
    sample_csv = tmp_path / "test_data.csv"
    sample_csv.write_text(
        "Company ,Year,Category,Current Ratio,Debt/Equity Ratio,ROE,ROA,Net Profit Margin,Gross Profit,Revenue\n"
        "TEST,2022,IT,1.5,0.8,15.0,8.0,12.0,4000,10000\n"
        "TEST,2021,IT,1.2,1.0,10.0,5.0,8.0,3000,8000\n",
        encoding="utf-8"
    )

    feats, meta = FeatureBuilder.build_features_from_csv(sample_csv)
    assert list(feats.columns) == ML_FEATURE_NAMES
    assert len(feats) == 2
    assert meta.iloc[0]["Company"] == "TEST"
    assert meta.iloc[0]["Year"] == 2022

    # Check derived gross profit margin: (4000 / 10000) * 100 = 40.0
    assert feats.iloc[0]["gross_profit_margin"] == 40.0
    # (3000 / 8000) * 100 = 37.5
    assert feats.iloc[1]["gross_profit_margin"] == 37.5


def test_feature_builder_missing_handling(tmp_path):
    """Verify deterministic imputation for missing values in CSV."""
    sample_csv = tmp_path / "test_missing.csv"
    sample_csv.write_text(
        "Company ,Year,Category,Current Ratio,Debt/Equity Ratio,ROE,ROA,Net Profit Margin,Gross Profit,Revenue\n"
        "TEST,2022,IT,2.0,0.5,12.0,6.0,10.0,500,1000\n"
        "TEST,2021,IT,,0.5,12.0,6.0,10.0,500,1000\n",
        encoding="utf-8"
    )

    feats, _ = FeatureBuilder.build_features_from_csv(sample_csv, handle_missing=True)
    assert not feats.isnull().any().any()
    # Imputed value should be median (2.0)
    assert feats.iloc[1]["current_ratio"] == 2.0


def test_extract_features_from_agent1_dict():
    """Verify extraction of feature vector from Agent 1 result dictionary."""
    agent1_payload = {
        "document_id": "test-uuid",
        "agent": "Agent 1",
        "status": "COMPLETED",
        "results": {
            "financial_ratios": {
                "ratios": {
                    "liquidity": {
                        "current_ratio": {"value": 1.85}
                    },
                    "leverage": {
                        "debt_to_equity": {"value": 0.42}
                    },
                    "profitability": {
                        "return_on_equity": {"value": 14.5},
                        "return_on_assets": {"value": 7.2},
                        "net_profit_margin": {"value": 11.3},
                        "gross_profit_margin": {"value": 45.0},
                    }
                }
            }
        }
    }

    vec = FeatureBuilder.extract_features_from_agent1_dict(agent1_payload)
    assert isinstance(vec, list)
    assert len(vec) == 6
    assert vec == [1.85, 0.42, 14.5, 7.2, 11.3, 45.0]


def test_extract_features_from_agent1_dict_missing():
    """Verify fallback imputation when Agent 1 has missing/None ratio values."""
    agent1_payload = {
        "results": {
            "financial_ratios": {
                "ratios": {
                    "liquidity": {
                        "current_ratio": {"value": None}
                    }
                }
            }
        }
    }

    vec = FeatureBuilder.extract_features_from_agent1_dict(agent1_payload, handle_missing=True)
    assert len(vec) == 6
    # current_ratio fallback is 1.0
    assert vec[0] == 1.0

    with pytest.raises(ValueError, match="is missing"):
        FeatureBuilder.extract_features_from_agent1_dict(agent1_payload, handle_missing=False)
