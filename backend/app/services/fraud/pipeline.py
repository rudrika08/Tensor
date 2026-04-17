"""
Fraud Detection Pipeline — Phase 4
Runs all 4 fraud checkers and returns FraudAssessment dict.
"""
import logging
from typing import List, Optional
from app.services.fraud.consistency_checker import check_consistency
from app.services.fraud.temporal_checker import check_temporal
from app.services.fraud.lighting_checker import check_lighting
from app.services.fraud.cross_signal_validator import check_cross_signals

logger = logging.getLogger(__name__)

RISK_WEIGHTS = {"critical": 4, "high": 2, "medium": 1, "low": 0}


def run_fraud_pipeline(
    image_paths: List[str],
    exif_timestamps: List[Optional[str]],
    vision_signals: dict,
    geo_signals: dict,
    years_in_operation: Optional[int] = None,
    claimed_floor_area: Optional[float] = None,
) -> dict:
    all_flags = []
    checker_results = {}

    # ── Checker 1: Multi-image consistency ───────────────────────────────
    c1 = check_consistency(image_paths, vision_signals)
    checker_results["consistency"] = c1
    all_flags.extend(c1.get("flags", []))

    # ── Checker 2: Temporal EXIF ──────────────────────────────────────────
    c2 = check_temporal(exif_timestamps)
    checker_results["temporal"] = c2
    all_flags.extend(c2.get("flags", []))

    # ── Checker 3: Lighting histogram ────────────────────────────────────
    c3 = check_lighting(image_paths)
    checker_results["lighting"] = c3
    all_flags.extend(c3.get("flags", []))

    # ── Checker 4: Cross-signal economic logic ───────────────────────────
    c4 = check_cross_signals(
        vision_signals=vision_signals,
        geo_signals=geo_signals,
        years_in_operation=years_in_operation,
        claimed_floor_area=claimed_floor_area,
    )
    checker_results["cross_signal"] = c4
    all_flags.extend(c4.get("flags", []))

    # ── Aggregate risk level ──────────────────────────────────────────────
    flag_count = len(all_flags)
    critical_flags = [f for f in all_flags if "critical" in f.lower()]

    if critical_flags or flag_count >= 4:
        risk_level = "critical"
        confidence = 0.95
    elif flag_count >= 3:
        risk_level = "high"
        confidence = 0.85
    elif flag_count >= 2:
        risk_level = "medium"
        confidence = 0.70
    elif flag_count == 1:
        risk_level = "low"
        confidence = 0.60
    else:
        risk_level = "low"
        confidence = 0.30

    return {
        "risk_level": risk_level,
        "flags": all_flags,
        "flag_count": flag_count,
        "confidence": confidence,
        "checker_results": checker_results,
    }
