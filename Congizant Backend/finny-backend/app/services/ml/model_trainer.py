"""Model trainer for Isolation Forest ML model.

Trains unsupervised Isolation Forest anomaly detection model using the
canonical feature schema on Financial Statements.csv and exports model,
schema, and metadata artifacts.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, Union
import joblib
import pandas as pd
import sklearn
from sklearn.ensemble import IsolationForest

from app.services.ml.feature_schema import (
    ML_FEATURE_NAMES,
    get_feature_schema_dict,
)
from app.services.ml.feature_builder import FeatureBuilder


class ModelTrainer:
    """Trainer and serializer for Isolation Forest anomaly detection."""

    DEFAULT_RANDOM_STATE = 42
    DEFAULT_CONTAMINATION = "auto"
    DEFAULT_N_ESTIMATORS = 100

    @classmethod
    def train_and_save(
        cls,
        csv_path: Union[str, Path] = "Financial Statements.csv",
        output_dir: Union[str, Path] = "ml_models",
        random_state: int = DEFAULT_RANDOM_STATE,
        contamination: Union[str, float] = DEFAULT_CONTAMINATION,
        n_estimators: int = DEFAULT_N_ESTIMATORS,
    ) -> Dict[str, Any]:
        """Train Isolation Forest on dataset and save model + metadata.

        Returns:
            Dictionary of training summary and evaluation metrics.
        """
        csv_p = Path(csv_path)
        out_p = Path(output_dir)
        out_p.mkdir(parents=True, exist_ok=True)

        # 1. Build features strictly according to canonical schema
        features_df, metadata_df = FeatureBuilder.build_features_from_csv(csv_p)

        # 2. Fit unsupervised Isolation Forest
        model = IsolationForest(
            n_estimators=n_estimators,
            contamination=contamination,
            random_state=random_state,
            n_jobs=-1,
        )
        model.fit(features_df)

        # 3. Compute unsupervised scores and predictions
        predictions = model.predict(features_df)  # 1 = normal, -1 = anomaly
        decision_scores = model.decision_function(features_df)

        normal_count = int((predictions == 1).sum())
        anomaly_count = int((predictions == -1).sum())
        total_count = len(predictions)
        anomaly_pct = round((anomaly_count / total_count) * 100.0, 4)

        score_min = float(decision_scores.min())
        score_max = float(decision_scores.max())
        score_mean = float(decision_scores.mean())
        score_std = float(decision_scores.std())

        # 4. Serialize model file via joblib
        model_path = out_p / "isolation_forest.joblib"
        joblib.dump(model, model_path)

        # 5. Export canonical feature schema JSON
        schema_path = out_p / "feature_schema.json"
        with open(schema_path, "w", encoding="utf-8") as f:
            json.dump(get_feature_schema_dict(), f, indent=2)

        # 6. Export comprehensive model metadata JSON
        training_metadata: Dict[str, Any] = {
            "model_type": "IsolationForest",
            "algorithm": "sklearn.ensemble.IsolationForest",
            "sklearn_version": sklearn.__version__,
            "joblib_version": joblib.__version__,
            "training_dataset": csv_p.name,
            "training_timestamp": datetime.now(timezone.utc).isoformat(),
            "random_state": random_state,
            "contamination": contamination,
            "n_estimators": n_estimators,
            "feature_names": ML_FEATURE_NAMES,
            "feature_count": len(ML_FEATURE_NAMES),
            "training_rows": total_count,
            "normal_count": normal_count,
            "anomaly_count": anomaly_count,
            "anomaly_percentage": anomaly_pct,
            "score_distribution": {
                "min": score_min,
                "max": score_max,
                "mean": score_mean,
                "std": score_std,
            },
            "interpretation_note": (
                "Unsupervised anomaly detection: observations with score < 0 (label -1) "
                "are statistically unusual relative to the training distribution, "
                "not confirmed fraud or errors."
            ),
        }

        metadata_path = out_p / "model_metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(training_metadata, f, indent=2)

        # 7. Build summary inspection records (sample anomalies & normals)
        inspection_records = []
        for idx in range(len(features_df)):
            inspection_records.append({
                "company": metadata_df.iloc[idx].get("Company", "Unknown"),
                "year": int(metadata_df.iloc[idx].get("Year", 0)),
                "score": round(float(decision_scores[idx]), 6),
                "prediction": int(predictions[idx]),
                "label": "anomaly" if predictions[idx] == -1 else "normal",
            })

        return {
            "model_path": str(model_path),
            "schema_path": str(schema_path),
            "metadata_path": str(metadata_path),
            "training_metadata": training_metadata,
            "inspection_records": inspection_records,
        }
