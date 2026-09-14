"""Model loader for Isolation Forest ML model.

Loads serialized IsolationForest model, validates feature vector alignment
against the authoritative feature schema, and provides inference methods.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import joblib
import pandas as pd
import numpy as np

from app.services.ml.feature_schema import ML_FEATURE_NAMES


class ModelLoader:
    """Safe loader and predictor for Isolation Forest."""

    def __init__(self, model_dir: Union[str, Path] = "ml_models"):
        self.model_dir = Path(model_dir)
        self.model_path = self.model_dir / "isolation_forest.joblib"
        self.metadata_path = self.model_dir / "model_metadata.json"
        self.schema_path = self.model_dir / "feature_schema.json"

        self._model = None
        self._metadata = None
        self._schema = None

    def is_model_available(self) -> bool:
        """Check if model and required metadata artifacts exist on disk."""
        return (
            self.model_path.exists()
            and self.metadata_path.exists()
            and self.schema_path.exists()
        )

    def load(self):
        """Load model, metadata, and feature schema into memory."""
        if not self.is_model_available():
            raise FileNotFoundError(
                f"Model artifacts not found in {self.model_dir}. "
                "Ensure ModelTrainer.train_and_save() has been run."
            )

        try:
            self._model = joblib.load(self.model_path)
        except Exception as load_err:
            raise ValueError(f"Corrupted or invalid model file: {str(load_err)}")

        try:
            with open(self.metadata_path, "r", encoding="utf-8") as f:
                self._metadata = json.load(f)
        except Exception as meta_err:
            raise ValueError(f"Corrupted or invalid model metadata JSON: {str(meta_err)}")

        try:
            with open(self.schema_path, "r", encoding="utf-8") as f:
                self._schema = json.load(f)
        except Exception as schema_err:
            raise ValueError(f"Corrupted or invalid feature schema JSON: {str(schema_err)}")

        # Validate loaded feature names match code feature names exactly in count and order
        loaded_features = self._metadata.get("feature_names", [])
        if not isinstance(loaded_features, list) or loaded_features != ML_FEATURE_NAMES:
            raise ValueError(
                f"Feature schema mismatch! Model trained with {loaded_features}, "
                f"current schema requires {ML_FEATURE_NAMES}"
            )

        if len(loaded_features) != len(ML_FEATURE_NAMES):
            raise ValueError(
                f"Feature count mismatch: model has {len(loaded_features)} features, "
                f"expected {len(ML_FEATURE_NAMES)}"
            )

    @property
    def model(self):
        if self._model is None:
            self.load()
        return self._model

    @property
    def metadata(self) -> Dict[str, Any]:
        if self._metadata is None:
            self.load()
        return self._metadata

    def predict_vector(self, feature_vector: List[float]) -> Dict[str, Any]:
        """Generate anomaly score and prediction for a single feature vector.

        Args:
            feature_vector: List of float values strictly ordered by ML_FEATURE_NAMES.

        Returns:
            Dictionary containing prediction (1 or -1), score (float), and normalized label.
        """
        if len(feature_vector) != len(ML_FEATURE_NAMES):
            raise ValueError(
                f"Input vector length {len(feature_vector)} does not match schema "
                f"length {len(ML_FEATURE_NAMES)}"
            )

        # Check for NaN / Inf
        arr = np.array(feature_vector, dtype=float)
        if np.isnan(arr).any() or np.isinf(arr).any():
            raise ValueError("Feature vector contains NaN or Infinity values")

        # Pass as DataFrame with exact feature names to preserve feature alignment without warnings
        df_input = pd.DataFrame([arr], columns=ML_FEATURE_NAMES)

        raw_pred = int(self.model.predict(df_input)[0])
        score = float(self.model.decision_function(df_input)[0])

        return {
            "prediction": raw_pred,  # 1 = normal, -1 = anomaly
            "score": round(score, 6),
            "label": "anomaly" if raw_pred == -1 else "normal",
            "is_anomaly": (raw_pred == -1),
        }
