import os
import uuid
import aiofiles
from pathlib import Path
from fastapi import UploadFile
from app.core.config import settings


async def save_image(file: UploadFile, submission_id: str, index: int) -> str:
    """
    Save an uploaded image to local storage (or S3 in production).
    Returns the storage path/key.
    """
    ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
    filename = f"{index}{ext}"
    key = f"submissions/{submission_id}/{filename}"

    if settings.STORAGE_BACKEND == "local":
        local_path = Path(settings.LOCAL_UPLOAD_DIR) / "submissions" / submission_id
        local_path.mkdir(parents=True, exist_ok=True)
        full_path = local_path / filename
        async with aiofiles.open(full_path, "wb") as f:
            content = await file.read()
            await f.write(content)
        return str(full_path)

    # S3 fallback
    import boto3
    content = await file.read()
    s3 = boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )
    s3.put_object(Bucket=settings.AWS_BUCKET_NAME, Key=key, Body=content)
    return f"s3://{settings.AWS_BUCKET_NAME}/{key}"


def get_image_local_path(storage_path: str) -> str:
    """Resolve a storage path to a local filesystem path for model inference."""
    if storage_path.startswith("s3://"):
        raise NotImplementedError("S3 path resolution not yet implemented")
    return storage_path
