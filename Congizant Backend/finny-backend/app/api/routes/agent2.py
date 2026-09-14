"""API routes for Agent 2 — AI Financial Review Agent."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_optional_user
from app.database.database import get_db
from app.models.user import User
from app.api.common import (
    get_normalized_document_and_record,
    persist_analysis_section,
    persist_ml_section,
    persist_review_observations_section,
)
from app.schemas.agent2 import Agent2ReviewResponse
from app.schemas.review_observations import ReviewObservationsResponse
from app.services.agent1.result_builder import Agent1ResultBuilder
from app.services.agent1.findings_builder import FindingsBuilder
from app.services.ml.anomaly_detector import AnomalyDetector
from app.services.ml.anomaly_result_builder import AnomalyResultBuilder
from app.services.agent2.review_agent import Agent2ReviewAgent
from app.services.review.review_observations_builder import ReviewObservationsBuilder
from app.services.agent2.ollama_client import (
    OllamaUnavailableException,
    OllamaTimeoutException,
    OllamaMalformedResponseException,
)

router = APIRouter()
logger = logging.getLogger(__name__)
anomaly_detector = AnomalyDetector()


@router.post(
    "/{document_id}/review",
    response_model=Agent2ReviewResponse,
    summary="Generate AI Financial Review with Local Ollama",
    description=(
        "Executes Agent 2 AI financial review using local Ollama. Investigates verified "
        "Agent 1 findings, performs pairwise metric comparisons, constructs grounded context, "
        "and produces structured review observations. Atomically persists outcome under "
        "normalized_data['analysis']['agent2']."
    )
)
def execute_agent2_review(document_id: str, db: Session = Depends(get_db), user: Optional[User] = Depends(get_optional_user)):
    """Orchestrate Agent 2 review for a normalized document."""
    # 1. Strict UUID validation, existence check, and NORMALIZED state enforcement with auth
    doc, fin_record = get_normalized_document_and_record(document_id, db, user)

    norm_data = dict(fin_record.normalized_data or {})
    analysis = dict(norm_data.get("analysis", {}) or {})
    agent1_findings = analysis.get("agent1_findings")

    # 2. Check if Agent 1 findings already exist; if not, build them
    if not agent1_findings:
        agent1_data = analysis.get("agent1")
        if not agent1_data:
            try:
                agent1_data = Agent1ResultBuilder.build_from_record(
                    document_id=doc.id,
                    fin_record=fin_record,
                    db=db,
                )
                persist_analysis_section(
                    fin_record=fin_record,
                    db=db,
                    section_key="agent1",
                    section_data=agent1_data,
                    document_id=doc.id
                )
                norm_data = dict(fin_record.normalized_data or {})
                analysis = dict(norm_data.get("analysis", {}) or {})
            except Exception as a1_err:
                logger.error("Failed to generate prerequisite Agent 1 data for doc %s: %s", doc.id, a1_err)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to generate prerequisite Agent 1 analytics: {str(a1_err)}"
                )

        ml_data = norm_data.get("ml_anomaly")
        if not ml_data:
            try:
                raw_ml_result = anomaly_detector.detect_anomalies(
                    agent1_data=agent1_data,
                    document_id=doc.id
                )
                ml_data = AnomalyResultBuilder.build_result(
                    document_id=doc.id,
                    inference_output=raw_ml_result
                )
                persist_ml_section(
                    fin_record=fin_record,
                    db=db,
                    ml_data=ml_data,
                    document_id=doc.id
                )
                norm_data = dict(fin_record.normalized_data or {})
            except Exception as ml_err:
                logger.warning("Could not auto-generate ML anomaly for doc %s: %s", doc.id, ml_err)

        try:
            agent1_findings = FindingsBuilder.build_findings(
                document_id=doc.id,
                norm_data=norm_data,
            )
            persist_analysis_section(
                fin_record=fin_record,
                db=db,
                section_key="agent1_findings",
                section_data=agent1_findings,
                document_id=doc.id
            )
            norm_data = dict(fin_record.normalized_data or {})
            analysis = dict(norm_data.get("analysis", {}) or {})
        except Exception as f_err:
            logger.exception("Failed to build prerequisite findings for doc %s: %s", doc.id, f_err)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate prerequisite findings: {str(f_err)}"
            )

    # 3. Execute Agent 2 Review
    try:
        review_result = Agent2ReviewAgent.review_document(
            document_id=doc.id,
            findings_data=agent1_findings,
        )
    except OllamaUnavailableException as una_err:
        logger.error("Ollama unavailable for doc %s: %s", doc.id, una_err)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Local Ollama service is unavailable: {str(una_err)}"
        )
    except OllamaTimeoutException as to_err:
        logger.error("Ollama timed out for doc %s: %s", doc.id, to_err)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Local Ollama service timed out during review: {str(to_err)}"
        )
    except OllamaMalformedResponseException as mal_err:
        logger.error("Malformed Ollama response for doc %s: %s", doc.id, mal_err)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Local Ollama returned a malformed or invalid response: {str(mal_err)}"
        )
    except Exception as exc:
        logger.exception("Unexpected failure in Agent 2 review for doc %s: %s", doc.id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during Agent 2 review: {str(exc)}"
        )

    # 4. Atomically persist review outcome under normalized_data['analysis']['agent2']
    persist_analysis_section(
        fin_record=fin_record,
        db=db,
        section_key="agent2",
        section_data=review_result,
        document_id=doc.id
    )

    return Agent2ReviewResponse(**review_result)


@router.post(
    "/{document_id}/observations",
    response_model=ReviewObservationsResponse,
    summary="Generate Structured Review Observations (Step 4.2)",
    description=(
        "Compiles final structured review observations based on verified Agent 1 Findings "
        "and Agent 2 Review. Generates grounded explanations and recommendations with "
        "deterministic severity ratings. Atomically persists under normalized_data['review_observations']."
    )
)
def execute_review_observations(document_id: str, db: Session = Depends(get_db), user: Optional[User] = Depends(get_optional_user)):
    """Orchestrate Review Observations for a normalized document."""
    # 1. Strict UUID validation, existence check, and NORMALIZED state enforcement with auth
    doc, fin_record = get_normalized_document_and_record(document_id, db, user)

    norm_data = dict(fin_record.normalized_data or {})
    analysis = dict(norm_data.get("analysis", {}) or {})
    agent1_findings = analysis.get("agent1_findings")
    agent2_data = analysis.get("agent2")

    # 2. Ensure Agent 1 Findings exist (or auto-generate)
    if not agent1_findings:
        agent1_data = analysis.get("agent1")
        if not agent1_data:
            try:
                agent1_data = Agent1ResultBuilder.build_from_record(
                    document_id=doc.id,
                    fin_record=fin_record,
                    db=db,
                )
                persist_analysis_section(
                    fin_record=fin_record,
                    db=db,
                    section_key="agent1",
                    section_data=agent1_data,
                    document_id=doc.id
                )
                norm_data = dict(fin_record.normalized_data or {})
                analysis = dict(norm_data.get("analysis", {}) or {})
            except Exception as a1_err:
                logger.error("Failed to generate prerequisite Agent 1 data for doc %s: %s", doc.id, a1_err)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to generate prerequisite Agent 1 analytics: {str(a1_err)}"
                )

        ml_data = norm_data.get("ml_anomaly")
        if not ml_data:
            try:
                raw_ml_result = anomaly_detector.detect_anomalies(
                    agent1_data=agent1_data,
                    document_id=doc.id
                )
                ml_data = AnomalyResultBuilder.build_result(
                    document_id=doc.id,
                    inference_output=raw_ml_result
                )
                persist_ml_section(
                    fin_record=fin_record,
                    db=db,
                    ml_data=ml_data,
                    document_id=doc.id
                )
                norm_data = dict(fin_record.normalized_data or {})
            except Exception as ml_err:
                logger.warning("Could not auto-generate ML anomaly for doc %s: %s", doc.id, ml_err)

        try:
            agent1_findings = FindingsBuilder.build_findings(
                document_id=doc.id,
                norm_data=norm_data,
            )
            persist_analysis_section(
                fin_record=fin_record,
                db=db,
                section_key="agent1_findings",
                section_data=agent1_findings,
                document_id=doc.id
            )
            norm_data = dict(fin_record.normalized_data or {})
            analysis = dict(norm_data.get("analysis", {}) or {})
        except Exception as f_err:
            logger.exception("Failed to build prerequisite findings for doc %s: %s", doc.id, f_err)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate prerequisite findings: {str(f_err)}"
            )

    # 3. Build Review Observations using local Ollama
    try:
        obs_result = ReviewObservationsBuilder.build_observations(
            document_id=doc.id,
            findings_data=agent1_findings,
            agent2_data=agent2_data,
        )
    except OllamaUnavailableException as una_err:
        logger.error("Ollama unavailable for doc %s: %s", doc.id, una_err)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Local Ollama service is unavailable: {str(una_err)}"
        )
    except OllamaTimeoutException as to_err:
        logger.error("Ollama timed out for doc %s: %s", doc.id, to_err)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Local Ollama service timed out during review observations: {str(to_err)}"
        )
    except OllamaMalformedResponseException as mal_err:
        logger.error("Malformed Ollama response for doc %s: %s", doc.id, mal_err)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Local Ollama returned a malformed or invalid response: {str(mal_err)}"
        )
    except Exception as exc:
        logger.exception("Unexpected error compiling review observations for doc %s: %s", doc.id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during review observations generation: {str(exc)}"
        )

    # 4. Atomically persist under normalized_data['review_observations']
    persist_review_observations_section(
        fin_record=fin_record,
        db=db,
        observations_data=obs_result,
        document_id=doc.id
    )

    return ReviewObservationsResponse(**obs_result)
