"""
EXIF temporal checker.
All images from a single visit should be within 30 minutes.
"""
import logging
from typing import List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

EXIF_DATE_FORMATS = [
    "%Y:%m:%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
]


def parse_exif_timestamp(ts: str) -> Optional[datetime]:
    for fmt in EXIF_DATE_FORMATS:
        try:
            return datetime.strptime(ts.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None


def check_temporal(exif_timestamps: List[Optional[str]]) -> dict:
    flags = []
    details = {}

    valid_ts = [ts for ts in exif_timestamps if ts]
    missing_count = len(exif_timestamps) - len(valid_ts)

    details["total_images"] = len(exif_timestamps)
    details["images_with_exif"] = len(valid_ts)
    details["images_missing_exif"] = missing_count

    # Flag missing EXIF (soft signal — could be screenshots or web-sourced)
    if missing_count > 0:
        flags.append("missing_exif_metadata")
        details["missing_exif_note"] = f"{missing_count} image(s) have no EXIF timestamp"

    # Parse timestamps
    parsed = []
    for ts in valid_ts:
        dt = parse_exif_timestamp(ts)
        if dt:
            parsed.append(dt)

    if len(parsed) >= 2:
        parsed.sort()
        gap = (parsed[-1] - parsed[0]).total_seconds() / 60  # minutes
        details["timestamp_gap_minutes"] = round(gap, 1)
        details["earliest"] = parsed[0].isoformat()
        details["latest"] = parsed[-1].isoformat()

        if gap > 30:
            flags.append("temporal_gap_detected")
            details["temporal_gap_reason"] = f"Images span {gap:.1f} minutes (threshold: 30 min)"

        if gap > 24 * 60:  # More than 1 day
            flags.append("critical_temporal_gap")
            details["critical_note"] = "Images taken on different days"

    return {"flags": flags, "details": details}
