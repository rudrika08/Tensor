"""
Pipeline runner — orchestrates all phases for a given submission.
Runs as a FastAPI BackgroundTask.
"""
import logging
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.submission import Submission, SubmissionStatus, Recommendation, RiskLevel

logger = logging.getLogger(__name__)


async def run_full_pipeline(submission_id: str):
    """
    Full async pipeline: Vision → Geo → Fraud → Fusion → Output
    """
    async with AsyncSessionLocal() as db:
        try:
            # Load submission
            result = await db.execute(select(Submission).where(Submission.id == submission_id))
            submission = result.scalar_one_or_none()
            if not submission:
                logger.error(f"Submission {submission_id} not found in pipeline runner")
                return

            image_paths = [r["path"] for r in (submission.image_records or []) if r.get("valid")]
            image_labels = [r["label"] for r in (submission.image_records or []) if r.get("valid")]
            exif_timestamps = [r.get("exif_timestamp") for r in (submission.image_records or []) if r.get("valid")]

            # ── Phase 2: Vision Engine ────────────────────────────────────
            from app.services.vision.pipeline import run_vision_pipeline
            vision_signals = await run_vision_pipeline(image_paths, image_labels)
            submission.vision_signals = vision_signals
            await db.commit()
            logger.info(f"[{submission_id}] Vision signals computed")

            # ── Phase 3: Geo Engine ───────────────────────────────────────
            from app.services.geo.pipeline import run_geo_pipeline
            geo_signals = await run_geo_pipeline(submission.latitude, submission.longitude)
            submission.geo_signals = geo_signals
            await db.commit()
            logger.info(f"[{submission_id}] Geo signals computed")

            # ── Phase 4: Fraud Detection ──────────────────────────────────
            from app.services.fraud.pipeline import run_fraud_pipeline
            fraud_assessment = run_fraud_pipeline(
                image_paths=image_paths,
                exif_timestamps=exif_timestamps,
                vision_signals=vision_signals,
                geo_signals=geo_signals,
                years_in_operation=submission.years_in_operation,
                claimed_floor_area=submission.claimed_floor_area_sqft,
            )
            submission.fraud_assessment = fraud_assessment
            await db.commit()
            logger.info(f"[{submission_id}] Fraud assessment done: {fraud_assessment.get('risk_level')}")

            # ── Phase 5: Multi-Modal Fusion ───────────────────────────────
            from app.services.fusion.pipeline import run_fusion_pipeline
            cash_flow = run_fusion_pipeline(vision_signals, geo_signals, fraud_assessment)
            submission.cash_flow_estimate = cash_flow
            await db.commit()
            logger.info(f"[{submission_id}] Cash flow estimated")

            # ── Phase 6: Output & Recommendation ─────────────────────────
            from app.services.output.json_builder import build_output
            from app.services.output.nlg import generate_explanation

            output = build_output(submission, vision_signals, geo_signals, fraud_assessment, cash_flow)
            explanation = generate_explanation(vision_signals, geo_signals, fraud_assessment, cash_flow)

            submission.output_json = output
            submission.explanation = explanation
            submission.recommendation = _derive_recommendation(fraud_assessment, cash_flow)
            submission.risk_level = _derive_risk_level(fraud_assessment)
            submission.status = SubmissionStatus.COMPLETED
            submission.error_message = None
            await db.commit()
            logger.info(f"[{submission_id}] Pipeline complete → {submission.recommendation}")

        except Exception as e:
            logger.exception(f"Pipeline failed for {submission_id}: {e}")
            async with AsyncSessionLocal() as err_db:
                result = await err_db.execute(select(Submission).where(Submission.id == submission_id))
                sub = result.scalar_one_or_none()
                if sub:
                    sub.status = SubmissionStatus.FAILED
                    sub.error_message = str(e)
                    await err_db.commit()


def _derive_recommendation(fraud: dict, cash_flow: dict) -> str:
    risk = fraud.get("risk_level", "low")
    flags = fraud.get("flags", [])
    confidence = cash_flow.get("confidence_score", 0.5)

    if risk == "critical" or len(flags) >= 3:
        return Recommendation.REJECT
    if risk == "high" or len(flags) >= 2:
        return Recommendation.REFER_FOR_FIELD_VISIT
    if risk == "medium" or confidence < 0.5:
        return Recommendation.APPROVE_WITH_MONITORING
    return Recommendation.APPROVE


def _derive_risk_level(fraud: dict) -> str:
    return fraud.get("risk_level", RiskLevel.LOW)
