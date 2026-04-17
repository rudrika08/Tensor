"""
Multi-image consistency checker.
Verifies inventory signals are consistent across multiple shelf images.
"""
import logging
import cv2
import numpy as np
from typing import List

logger = logging.getLogger(__name__)


def check_consistency(image_paths: List[str], vision_signals: dict) -> dict:
    flags = []
    details = {}

    shelf_paths = image_paths  # Use all images for now

    if len(shelf_paths) < 2:
        return {"flags": [], "details": {"message": "Only 1 image, cannot check consistency"}}

    # Compare edge densities across images as inventory proxy
    densities = []
    for path in shelf_paths:
        try:
            img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            edges = cv2.Canny(img, 50, 150)
            density = edges.sum() / (img.shape[0] * img.shape[1] * 255)
            densities.append(density)
        except Exception:
            continue

    if len(densities) >= 2:
        arr = np.array(densities)
        cv_ratio = arr.std() / (arr.mean() + 1e-6)  # Coefficient of variation
        details["edge_density_cv"] = round(float(cv_ratio), 4)
        details["per_image_densities"] = [round(d, 4) for d in densities]

        if cv_ratio > 0.4:
            flags.append("inventory_count_inconsistency")
            details["reason"] = f"Edge density variation {cv_ratio:.2f} exceeds 0.4 threshold"

    # Check SDI vs product count consistency
    sdi = vision_signals.get("sdi", 0.5)
    product_count = vision_signals.get("detected_product_count", 0)
    if sdi > 0.8 and product_count < 10:
        flags.append("sdi_product_count_mismatch")
        details["sdi_mismatch"] = f"High SDI ({sdi}) but low product count ({product_count})"

    return {"flags": flags, "details": details}
