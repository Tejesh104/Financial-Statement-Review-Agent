"""ML anomaly detector service.

Coordinates feature extraction from Agent 1 results, validation, model loading,
unsupervised anomaly prediction, and structured result construction.
"""

from typing import Dict, Any, List, Optional
import numpy as np

from app.services.ml.feature_schema import ML_FEATURE_NAMES, FEATURE_METADATA
from app.services.ml.feature_builder import FeatureBuilder, _safe_numeric
from app.services.ml.model_loader import ModelLoader


class AnomalyDetector:
    """Service for running Isolation Forest anomaly detection on Agent 1 data."""

    def __init__(self, model_loader: Optional[ModelLoader] = None):
        self.loader = model_loader or ModelLoader()

    def detect_anomalies(
        self,
        agent1_data: Dict[str, Any],
        document_id: str
    ) -> Dict[str, Any]:
        """Perform anomaly detection using pre-trained Isolation Forest on Agent 1 results.

        Args:
            agent1_data: The structured dictionary output from Agent 1 Result Builder.
            document_id: The document UUID.

        Returns:
            Structured dictionary compliant with MLAnomalyResponse.
        """
        # 1. Check model availability
        if not self.loader.is_model_available():
            raise FileNotFoundError(
                "Trained Isolation Forest model artifacts are not available on disk. "
                "Ensure training pipeline has been executed."
            )

        # 2. Extract raw features from Agent 1 ratios
        ratios_block = (
            agent1_data.get("results", {})
            .get("financial_ratios", {})
            .get("ratios", {})
        )
        liquidity = ratios_block.get("liquidity", {})
        leverage = ratios_block.get("leverage", {})
        profitability = ratios_block.get("profitability", {})

        raw_features: Dict[str, Optional[float]] = {
            "current_ratio": _safe_numeric(liquidity.get("current_ratio", {}).get("value")),
            "debt_to_equity": _safe_numeric(leverage.get("debt_to_equity", {}).get("value")),
            "roe": _safe_numeric(profitability.get("return_on_equity", {}).get("value")),
            "roa": _safe_numeric(profitability.get("return_on_assets", {}).get("value")),
            "net_profit_margin": _safe_numeric(profitability.get("net_profit_margin", {}).get("value")),
            "gross_profit_margin": _safe_numeric(profitability.get("gross_profit_margin", {}).get("value")),
        }

        # 3. Check for missing or undefined ratios
        warnings: List[str] = []
        missing_features: List[str] = []
        imputed_features: Dict[str, float] = {}

        feature_vector: List[float] = []
        for feat in ML_FEATURE_NAMES:
            val = raw_features.get(feat)
            if val is None:
                missing_features.append(feat)
                default_val = float(FEATURE_METADATA[feat]["default_imputation"])
                feature_vector.append(default_val)
                imputed_features[feat] = default_val
                warnings.append(
                    f"Feature '{feat}' was unavailable from Agent 1 ratios; "
                    f"used neutral baseline {default_val} for anomaly inference."
                )
            else:
                feature_vector.append(float(val))

        # 4. Strict numerical sanity check
        arr = np.array(feature_vector, dtype=float)
        if np.isnan(arr).any() or np.isinf(arr).any():
            raise ValueError("Constructed ML feature vector contains NaN or Infinity values")

        # 5. Run prediction via ModelLoader
        pred_res = self.loader.predict_vector(feature_vector)

        # 6. Retrieve metadata
        meta = self.loader.metadata
        model_info = {
            "type": meta.get("model_type", "IsolationForest"),
            "version": meta.get("sklearn_version", "unknown"),
            "training_dataset": meta.get("training_dataset", "Financial Statements.csv"),
            "feature_count": len(ML_FEATURE_NAMES),
        }

        # If any features were missing, status is INCOMPLETE, else COMPLETED
        status = "INCOMPLETE" if missing_features else "COMPLETED"
        reason = None
        if missing_features:
            reason = f"Analysis completed with imputed baselines for missing ratios: {', '.join(missing_features)}."

        return {
            "document_id": document_id,
            "status": status,
            "model": model_info,
            "features": raw_features,
            "anomaly_detection": pred_res,
            "warnings": warnings,
            "reason": reason,
        }
