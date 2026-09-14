"""API router for ML anomaly detection."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_optional_user
from app.database.database import get_db
from app.models.user import User
from app.api.common import get_normalized_document_and_record, persist_ml_section
from app.schemas.ml import MLAnomalyResponse
from app.services.agent1.result_builder import Agent1ResultBuilder
from app.services.ml.anomaly_detector import AnomalyDetector
from app.services.ml.anomaly_result_builder import AnomalyResultBuilder

logger = logging.getLogger(__name__)

router = APIRouter()
anomaly_detector = AnomalyDetector()


@router.post(
    "/{document_id}/anomaly",
    response_model=MLAnomalyResponse,
    summary="Detect statistical anomalies in normalized financial statements",
    description=(
        "Executes pre-trained Isolation Forest anomaly detection against canonical "
        "financial ratios computed by Agent 1. Returns anomaly score, binary label, "
        "and interpretation. Persists outcome under normalized_data['ml_anomaly']."
    ),
)
def detect_document_anomaly(document_id: str, db: Session = Depends(get_db), user: Optional[User] = Depends(get_optional_user)):
    """Evaluate financial statement for statistical anomalies using Isolation Forest."""
    # 1. Strict UUID validation, existence check, and NORMALIZED status enforcement with auth
    doc, fin_record = get_normalized_document_and_record(document_id, db, user)

    # 2. Check if Agent 1 results already exist in normalized_data or compute them
    norm_data = dict(fin_record.normalized_data or {})
    agent1_data = norm_data.get("analysis", {}).get("agent1")

    if not agent1_data:
        try:
            agent1_data = Agent1ResultBuilder.build_from_record(
                document_id=doc.id,
                fin_record=fin_record,
                db=db,
            )
        except Exception as a1_err:
            logger.error("Failed to build Agent 1 results for doc %s: %s", document_id, a1_err)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate prerequisites from Agent 1: {str(a1_err)}"
            )

    # 3. Execute ML Anomaly Detection inference
    try:
        raw_ml_result = anomaly_detector.detect_anomalies(
            agent1_data=agent1_data,
            document_id=doc.id
        )
        ml_result = AnomalyResultBuilder.build_result(
            document_id=doc.id,
            inference_output=raw_ml_result
        )
    except FileNotFoundError as fnf_err:
        logger.error("ML model files missing: %s", fnf_err)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ML anomaly detection model is not initialized or model artifacts are missing."
        )
    except ValueError as val_err:
        logger.warning("Feature vector or result validation failed for doc %s: %s", document_id, val_err)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid feature vector or result for anomaly detection: {str(val_err)}"
        )
    except Exception as exc:
        logger.exception("Unexpected error during anomaly detection for doc %s: %s", document_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during ML anomaly detection: {str(exc)}"
        )

    # 4. Atomically persist under normalized_data['ml_anomaly']
    persist_ml_section(
        fin_record=fin_record,
        db=db,
        ml_data=ml_result,
        document_id=doc.id
    )

    return MLAnomalyResponse(**ml_result)
