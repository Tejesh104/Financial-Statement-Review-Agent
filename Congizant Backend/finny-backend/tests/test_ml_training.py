"""Tests for Isolation Forest model training, serialization, loading, and predictability."""

import pytest
import json
from pathlib import Path
import numpy as np

from app.services.ml.feature_schema import ML_FEATURE_NAMES
from app.services.ml.model_trainer import ModelTrainer
from app.services.ml.model_loader import ModelLoader


@pytest.fixture(scope="module")
def trained_artifacts(tmp_path_factory):
    """Train model in a temporary directory for test isolation."""
    tmp_dir = tmp_path_factory.mktemp("ml_test_models")
    res = ModelTrainer.train_and_save(
        csv_path="Financial Statements.csv",
        output_dir=tmp_dir,
        random_state=42,
        contamination="auto",
        n_estimators=50  # Fast estimators for unit tests
    )
    return {
        "dir": tmp_dir,
        "res": res,
    }


def test_training_succeeds_and_creates_files(trained_artifacts):
    """Verify all 3 artifacts are generated."""
    tmp_dir = trained_artifacts["dir"]
    assert (tmp_dir / "isolation_forest.joblib").exists()
    assert (tmp_dir / "feature_schema.json").exists()
    assert (tmp_dir / "model_metadata.json").exists()


def test_model_metadata_content(trained_artifacts):
    """Verify metadata contains required properties without secrets."""
    meta_path = trained_artifacts["dir"] / "model_metadata.json"
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    assert meta["model_type"] == "IsolationForest"
    assert meta["training_dataset"] == "Financial Statements.csv"
    assert meta["training_rows"] == 161
    assert meta["feature_count"] == 6
    assert meta["feature_names"] == ML_FEATURE_NAMES
    assert meta["random_state"] == 42
    assert meta["contamination"] == "auto"
    assert meta["normal_count"] > 0
    assert meta["anomaly_count"] > 0
    assert meta["normal_count"] + meta["anomaly_count"] == 161
    assert 0 < meta["anomaly_percentage"] < 50
    assert "score_distribution" in meta
    assert meta["score_distribution"]["min"] < meta["score_distribution"]["max"]


def test_model_loader_availability(trained_artifacts):
    """Verify ModelLoader correctly reports availability."""
    loader = ModelLoader(model_dir=trained_artifacts["dir"])
    assert loader.is_model_available() is True

    fake_loader = ModelLoader(model_dir="non_existent_directory")
    assert fake_loader.is_model_available() is False


def test_model_loader_predictions(trained_artifacts):
    """Verify inference generates expected label and finite numeric score."""
    loader = ModelLoader(model_dir=trained_artifacts["dir"])
    loader.load()

    # Normal profile vector
    normal_vector = [1.5, 0.4, 15.0, 7.0, 12.0, 45.0]
    res = loader.predict_vector(normal_vector)

    assert "prediction" in res
    assert res["prediction"] in (1, -1)
    assert "score" in res
    assert isinstance(res["score"], float)
    assert not np.isnan(res["score"])
    assert not np.isinf(res["score"])
    assert res["label"] in ("normal", "anomaly")
    assert res["is_anomaly"] == (res["prediction"] == -1)


def test_deterministic_predictions(trained_artifacts):
    """Verify identical inputs yield identical predictions and scores."""
    loader = ModelLoader(model_dir=trained_artifacts["dir"])
    vector = [2.0, 0.8, 20.0, 10.0, 18.0, 50.0]

    res1 = loader.predict_vector(vector)
    res2 = loader.predict_vector(vector)

    assert res1["prediction"] == res2["prediction"]
    assert res1["score"] == res2["score"]


def test_vector_length_mismatch(trained_artifacts):
    """Verify error raised on invalid vector length."""
    loader = ModelLoader(model_dir=trained_artifacts["dir"])
    with pytest.raises(ValueError, match="does not match schema length"):
        loader.predict_vector([1.0, 2.0])


def test_vector_nan_inf_rejection(trained_artifacts):
    """Verify error raised when vector contains NaN or Inf."""
    loader = ModelLoader(model_dir=trained_artifacts["dir"])
    with pytest.raises(ValueError, match="NaN or Infinity"):
        loader.predict_vector([1.0, 0.5, float("nan"), 5.0, 10.0, 40.0])

    with pytest.raises(ValueError, match="NaN or Infinity"):
        loader.predict_vector([1.0, 0.5, float("inf"), 5.0, 10.0, 40.0])


def test_production_model_directory_artifacts():
    """Verify that train_model.py trained artifacts in the main ml_models/ directory."""
    main_loader = ModelLoader(model_dir="ml_models")
    assert main_loader.is_model_available() is True
    main_loader.load()
    assert main_loader.metadata["training_rows"] == 161
    assert main_loader.metadata["feature_names"] == ML_FEATURE_NAMES
