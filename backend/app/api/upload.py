import json
import uuid
from typing import List, Optional
from fastapi import APIRouter, File, Form, UploadFile, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.config import settings
from app.core.storage import save_image
from app.models.submission import Submission, SubmissionStatus
from app.models.schemas import SubmissionResponse, SubmissionDetail, SubmissionListItem
from app.services.image_validator import validate_image, apply_clahe
from app.services.pipeline_runner import run_full_pipeline

router = APIRouter(prefix="/api/v1/submissions", tags=["Submissions"])


@router.post("", response_model=SubmissionResponse, status_code=202)
async def create_submission(
    background_tasks: BackgroundTasks,
    images: List[UploadFile] = File(..., description="3–5 store images"),
    latitude: float = Form(...),
    longitude: float = Form(...),
    store_name: Optional[str] = Form(None),
    years_in_operation: Optional[int] = Form(None),
    claimed_floor_area_sqft: Optional[float] = Form(None),
    monthly_rent: Optional[float] = Form(None),
    image_labels: Optional[str] = Form(None, description='JSON array e.g. ["shelf","exterior","counter"]'),
    db: AsyncSession = Depends(get_db),
):
    # ── Validate image count ──────────────────────────────────────────────
    if len(images) < settings.MIN_IMAGES_PER_SUBMISSION:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum {settings.MIN_IMAGES_PER_SUBMISSION} images required. Got {len(images)}."
        )
    if len(images) > settings.MAX_IMAGES_PER_SUBMISSION:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {settings.MAX_IMAGES_PER_SUBMISSION} images allowed. Got {len(images)}."
        )

    # ── Parse user-provided labels ────────────────────────────────────────
    user_labels: List[Optional[str]] = []
    if image_labels:
        try:
            parsed = json.loads(image_labels)
            user_labels = parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            user_labels = []
    user_labels += [None] * (len(images) - len(user_labels))

    # ── Create DB record ──────────────────────────────────────────────────
    submission_id = str(uuid.uuid4())
    submission = Submission(
        id=submission_id,
        latitude=latitude,
        longitude=longitude,
        store_name=store_name,
        years_in_operation=years_in_operation,
        claimed_floor_area_sqft=claimed_floor_area_sqft,
        monthly_rent=monthly_rent,
        status=SubmissionStatus.VALIDATING,
    )
    db.add(submission)
    await db.flush()

    # ── Validate & save each image ────────────────────────────────────────
    image_records = []
    rejected = []

    for i, (upload, label_hint) in enumerate(zip(images, user_labels)):
        # MIME check
        if upload.content_type not in {"image/jpeg", "image/png", "image/webp"}:
            rejected.append(f"Image {i+1}: unsupported type {upload.content_type}")
            continue

        # Size check
        raw_bytes = await upload.read()
        if len(raw_bytes) > settings.MAX_IMAGE_SIZE_MB * 1024 * 1024:
            rejected.append(f"Image {i+1}: exceeds {settings.MAX_IMAGE_SIZE_MB}MB limit")
            continue

        # Validation pipeline
        result = validate_image(raw_bytes, user_label=label_hint)

        if not result.valid:
            rejected.append(f"Image {i+1}: {result.rejection_reason}")
            continue

        # Apply CLAHE enhancement before storage
        enhanced_bytes = apply_clahe(raw_bytes)

        # Save to storage
        upload.file.seek(0)
        import io
        upload.file = io.BytesIO(enhanced_bytes)
        upload.filename = f"img_{i}.jpg"
        path = await save_image(upload, submission_id, i)

        image_records.append({
            "path": path,
            "label": result.label,
            "blur_score": result.blur_score,
            "resolution": list(result.resolution),
            "valid": True,
            "exif_timestamp": result.exif_timestamp,
            "original_filename": upload.filename,
        })

    # ── Reject if too few valid images ────────────────────────────────────
    if len(image_records) < settings.MIN_IMAGES_PER_SUBMISSION:
        submission.status = SubmissionStatus.FAILED
        submission.error_message = f"Only {len(image_records)} valid images after validation. Rejected: {'; '.join(rejected)}"
        await db.commit()
        raise HTTPException(
            status_code=422,
            detail={
                "message": f"Insufficient valid images. Need {settings.MIN_IMAGES_PER_SUBMISSION}.",
                "rejected_reasons": rejected,
            }
        )

    # ── Update record and kick off async pipeline ─────────────────────────
    submission.image_records = image_records
    submission.status = SubmissionStatus.PROCESSING
    await db.commit()

    background_tasks.add_task(run_full_pipeline, str(submission.id))

    return SubmissionResponse(
        id=submission.id,
        created_at=submission.created_at,
        status=submission.status,
        latitude=submission.latitude,
        longitude=submission.longitude,
        store_name=submission.store_name,
        image_count=len(image_records),
        message="Submission accepted. Processing started.",
    )


@router.get("", response_model=List[SubmissionListItem])
async def list_submissions(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Submission).order_by(Submission.created_at.desc()).offset(skip).limit(limit)
    )
    submissions = result.scalars().all()
    return [
        SubmissionListItem(
            id=s.id,
            created_at=s.created_at,
            status=s.status,
            store_name=s.store_name,
            latitude=s.latitude,
            longitude=s.longitude,
            recommendation=s.recommendation,
            risk_level=s.risk_level,
        )
        for s in submissions
    ]


@router.get("/{submission_id}", response_model=SubmissionDetail)
async def get_submission(submission_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return SubmissionDetail(**submission.to_dict())


@router.get("/{submission_id}/status")
async def get_submission_status(submission_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Submission.id, Submission.status, Submission.error_message, Submission.recommendation)
        .where(Submission.id == submission_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Submission not found")
    return {
        "id": str(row.id),
        "status": row.status,
        "error_message": row.error_message,
        "recommendation": row.recommendation,
    }
