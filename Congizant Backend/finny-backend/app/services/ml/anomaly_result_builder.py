"""Anomaly result builder service for ML anomaly detection layer.

Transforms raw Isolation Forest inference results into canonical backend anomaly results.
Preserves existing decision scores, predictions, and status contracts without fabricating
arbitrary thresholds or probability claims.
"""

import math
from typing import Dict, Any, Optional, List

from app.schemas.ml import MLAnomalyResponse, AnomalyDetectionResult, ModelInfo


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


class AnomalyResultBuilder:
    """Service to construct standardized anomaly detection results."""

    CLASSIFICATION_NORMAL = "NORMAL"
    CLASSIFICATION_ANOMALY = "ANOMALY"

    @classmethod
    def build_result(
        cls,
        document_id: str,
        inference_output: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Convert raw ML anomaly detector output into standardized backend response structure.

        Args:
            document_id: UUID string of the document.
            inference_output: Dictionary returned by AnomalyDetector.detect_anomalies().

        Returns:
            Structured dictionary compliant with MLAnomalyResponse.
        """
        if not isinstance(inference_output, dict):
            raise ValueError("Inference output must be a dictionary.")

        # 1. Status preservation
        status = inference_output.get("status", "COMPLETED")
        if status not in ("COMPLETED", "INCOMPLETE", "ERROR"):
            status = "COMPLETED"

        # 2. Extract model info
        model_dict = inference_output.get("model", {})
        model_info = {
            "type": str(model_dict.get("type", "IsolationForest")),
            "version": str(model_dict.get("version", "unknown")),
            "training_dataset": str(model_dict.get("training_dataset", "Financial Statements.csv")),
            "feature_count": int(model_dict.get("feature_count", 6)),
        }

        # 3. Extract and validate features
        raw_features = inference_output.get("features", {})
        cleaned_features: Dict[str, Optional[float]] = {}
        if isinstance(raw_features, dict):
            for k, v in raw_features.items():
                cleaned_features[k] = _safe_float(v)

        # 4. Extract and validate core anomaly detection fields
        if "anomaly_detection" not in inference_output or not isinstance(inference_output["anomaly_detection"], dict):
            raise ValueError("Missing or malformed 'anomaly_detection' block in inference output.")

        ad_block = inference_output["anomaly_detection"]

        raw_pred = ad_block.get("prediction")
        if raw_pred not in (1, -1):
            raise ValueError(f"Invalid ML prediction '{raw_pred}'. Must be 1 (normal) or -1 (anomaly).")

        raw_score = _safe_float(ad_block.get("score"))
        if raw_score is None:
            raise ValueError("Missing, NaN, or non-finite anomaly score in inference output.")

        # Canonical classification: 1 -> NORMAL, -1 -> ANOMALY
        is_anomaly = (raw_pred == -1)
        classification = cls.CLASSIFICATION_ANOMALY if is_anomaly else cls.CLASSIFICATION_NORMAL
        label = "anomaly" if is_anomaly else "normal"

        anomaly_detection = {
            "prediction": raw_pred,
            "label": label,
            "classification": classification,
            "is_anomaly": is_anomaly,
            "score": round(raw_score, 6),
            "anomaly_score": round(raw_score, 6),
        }

        # 5. Warnings and reason
        warnings: List[str] = []
        for w in inference_output.get("warnings", []):
            if w and str(w).strip():
                warnings.append(str(w).strip())

        reason = inference_output.get("reason")

        # As documented: "UNUSUAL" is not defined as an independent statistical threshold
        # in the model metadata or project contract. Therefore, the binary Isolation Forest
        # classification (NORMAL / ANOMALY) is preserved with high-precision anomaly_score exposed.
        return {
            "document_id": document_id,
            "status": status,
            "classification": classification,
            "anomaly_score": round(raw_score, 6),
            "prediction": raw_pred,
            "is_anomaly": is_anomaly,
            "model": model_info,
            "features": cleaned_features,
            "anomaly_detection": anomaly_detection,
            "warnings": warnings,
            "reason": reason,
        }
