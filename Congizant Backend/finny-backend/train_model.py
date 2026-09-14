"""Standalone training runner for Isolation Forest anomaly detection."""

import sys
import json
from app.services.ml.model_trainer import ModelTrainer

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

print("==================================================")
print("FINNY BACKEND: ISOLATION FOREST MODEL TRAINING")
print("==================================================")

res = ModelTrainer.train_and_save(
    csv_path="Financial Statements.csv",
    output_dir="ml_models",
    random_state=42,
    contamination="auto",
    n_estimators=100
)

meta = res["training_metadata"]
print("\n--- MODEL METADATA ---")
print("Model Type:", meta["model_type"])
print("Dataset:", meta["training_dataset"])
print("Training Rows:", meta["training_rows"])
print("Features Count:", meta["feature_count"])
print("Features:", meta["feature_names"])
print("Random State:", meta["random_state"])
print("Contamination:", meta["contamination"])
print("Scikit-Learn Version:", meta["sklearn_version"])

print("\n--- UNSUPERVISED RESULTS ---")
print("Normal Observations:", meta["normal_count"])
print("Anomalies Detected:", meta["anomaly_count"])
print(f"Anomaly Percentage: {meta['anomaly_percentage']}%")
print("Score Distribution:")
print("  Min:", meta["score_distribution"]["min"])
print("  Max:", meta["score_distribution"]["max"])
print("  Mean:", meta["score_distribution"]["mean"])
print("  Std:", meta["score_distribution"]["std"])

print("\n--- PERSISTED ARTIFACTS ---")
print("Model:", res["model_path"])
print("Schema:", res["schema_path"])
print("Metadata:", res["metadata_path"])

print("\n--- TOP ANOMALIES INSPECTION ---")
records = res["inspection_records"]
anomalies = [r for r in records if r["prediction"] == -1]
anomalies.sort(key=lambda x: x["score"])

print(f"{'Company':<10} {'Year':<6} {'Score':<12} {'Prediction':<12} {'Label':<10}")
print("-" * 55)
for r in anomalies[:10]:
    print(f"{r['company']:<10} {r['year']:<6} {r['score']:<12.6f} {r['prediction']:<12} {r['label']:<10}")

print("\n--- SAMPLE NORMAL OBSERVATIONS ---")
normals = [r for r in records if r["prediction"] == 1]
normals.sort(key=lambda x: x["score"], reverse=True)
print(f"{'Company':<10} {'Year':<6} {'Score':<12} {'Prediction':<12} {'Label':<10}")
print("-" * 55)
for r in normals[:5]:
    print(f"{r['company']:<10} {r['year']:<6} {r['score']:<12.6f} {r['prediction']:<12} {r['label']:<10}")

print("\n==================================================")
print("TRAINING PROCESS COMPLETED SUCCESSFULLY")
print("==================================================")
