import io
import cv2
import numpy as np
import exifread
from PIL import Image
from pathlib import Path
from typing import Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

from app.core.config import settings


@dataclass
class ValidationResult:
    valid: bool
    label: str          # shelf | counter | exterior | unknown
    blur_score: float
    resolution: Tuple[int, int]
    exif_timestamp: Optional[str]
    rejection_reason: Optional[str] = None


def compute_blur_score(image_bytes: bytes) -> float:
    """Laplacian variance — higher = sharper."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return 0.0
    return float(cv2.Laplacian(img, cv2.CV_64F).var())


def get_resolution(image_bytes: bytes) -> Tuple[int, int]:
    """Return (width, height)."""
    img = Image.open(io.BytesIO(image_bytes))
    return img.size  # (width, height)


def extract_exif_timestamp(image_bytes: bytes) -> Optional[str]:
    """Extract DateTimeOriginal from EXIF."""
    try:
        tags = exifread.process_file(io.BytesIO(image_bytes), stop_tag="EXIF DateTimeOriginal", details=False)
        dt_tag = tags.get("EXIF DateTimeOriginal") or tags.get("Image DateTime")
        if dt_tag:
            return str(dt_tag)
    except Exception:
        pass
    return None


def classify_image_label(image_bytes: bytes) -> str:
    """
    Lightweight coverage type classifier using color/edge heuristics.
    Returns: shelf | counter | exterior | unknown

    In production this is replaced by CLIP zero-shot. Here we use a
    fast heuristic so validation works without heavy models loaded.
    """
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return "unknown"

        h, w = img.shape[:2]
        aspect = w / h

        # Edge density — shelves have many horizontal edges
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = edges.sum() / (h * w * 255)

        # Top-third vs bottom-third brightness ratio
        top_brightness = gray[: h // 3, :].mean()
        bottom_brightness = gray[2 * h // 3 :, :].mean()
        sky_ratio = top_brightness / (bottom_brightness + 1e-6)

        # Exterior: high sky brightness ratio, moderate edge density
        if sky_ratio > 1.4 and edge_density < 0.08:
            return "exterior"

        # Shelf: high edge density, portrait/square aspect
        if edge_density > 0.08 and aspect < 1.5:
            return "shelf"

        # Counter: moderate edges, landscape
        if edge_density > 0.04 and aspect >= 1.2:
            return "counter"

        return "unknown"
    except Exception:
        return "unknown"


def apply_clahe(image_bytes: bytes) -> bytes:
    """Apply CLAHE for low-light enhancement. Returns processed JPEG bytes."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return image_bytes
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_clahe = clahe.apply(l)
    enhanced = cv2.merge([l_clahe, a, b])
    result = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
    _, buf = cv2.imencode(".jpg", result, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return buf.tobytes()


def validate_image(image_bytes: bytes, user_label: Optional[str] = None) -> ValidationResult:
    """
    Full validation pipeline for a single image.
    Returns ValidationResult with valid flag and metadata.
    """
    # Resolution check
    try:
        resolution = get_resolution(image_bytes)
    except Exception:
        return ValidationResult(
            valid=False, label="unknown", blur_score=0.0,
            resolution=(0, 0), exif_timestamp=None,
            rejection_reason="Could not read image file"
        )

    w, h = resolution
    if w < settings.MIN_IMAGE_WIDTH or h < settings.MIN_IMAGE_HEIGHT:
        return ValidationResult(
            valid=False, label="unknown", blur_score=0.0,
            resolution=resolution, exif_timestamp=None,
            rejection_reason=f"Resolution too low: {w}×{h}. Minimum: {settings.MIN_IMAGE_WIDTH}×{settings.MIN_IMAGE_HEIGHT}"
        )

    # Blur check
    blur_score = compute_blur_score(image_bytes)
    if blur_score < settings.BLUR_THRESHOLD:
        return ValidationResult(
            valid=False, label="unknown", blur_score=blur_score,
            resolution=resolution, exif_timestamp=None,
            rejection_reason=f"Image too blurry (score: {blur_score:.1f}). Minimum: {settings.BLUR_THRESHOLD}"
        )

    # EXIF timestamp
    exif_ts = extract_exif_timestamp(image_bytes)

    # Coverage label
    label = user_label if user_label in {"shelf", "counter", "exterior"} else classify_image_label(image_bytes)

    return ValidationResult(
        valid=True,
        label=label,
        blur_score=round(blur_score, 2),
        resolution=resolution,
        exif_timestamp=exif_ts,
    )
