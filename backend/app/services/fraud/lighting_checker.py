"""
Lighting histogram consistency checker.
All images in a visit should have similar ambient light.
"""
import logging
import cv2
import numpy as np
from typing import List, Optional

logger = logging.getLogger(__name__)

LIGHTING_CORRELATION_THRESHOLD = 0.70


def compute_brightness_histogram(image_path: str) -> Optional[np.ndarray]:
    img = cv2.imread(image_path)
    if img is None:
        return None
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    v_channel = hsv[:, :, 2]
    hist = cv2.calcHist([v_channel], [0], None, [64], [0, 256])
    cv2.normalize(hist, hist)
    return hist.flatten()


def check_lighting(image_paths: List[str]) -> dict:
    flags = []
    details = {}

    if len(image_paths) < 2:
        return {"flags": [], "details": {"message": "Single image, cannot compare lighting"}}

    histograms = []
    for path in image_paths:
        hist = compute_brightness_histogram(path)
        if hist is not None:
            histograms.append(hist)

    if len(histograms) < 2:
        return {"flags": [], "details": {"message": "Could not compute histograms"}}

    # Pairwise correlation
    correlations = []
    for i in range(len(histograms)):
        for j in range(i + 1, len(histograms)):
            corr = cv2.compareHist(
                histograms[i].reshape(-1, 1).astype(np.float32),
                histograms[j].reshape(-1, 1).astype(np.float32),
                cv2.HISTCMP_CORREL
            )
            correlations.append(float(corr))

    avg_corr = float(np.mean(correlations))
    min_corr = float(np.min(correlations))
    details["avg_lighting_correlation"] = round(avg_corr, 4)
    details["min_lighting_correlation"] = round(min_corr, 4)
    details["pairwise_correlations"] = [round(c, 4) for c in correlations]

    if avg_corr < LIGHTING_CORRELATION_THRESHOLD:
        flags.append("lighting_inconsistency")
        details["lighting_reason"] = (
            f"Average lighting correlation {avg_corr:.2f} below threshold "
            f"{LIGHTING_CORRELATION_THRESHOLD}. Possible mixed daylight/artificial sources."
        )

    return {"flags": flags, "details": details}


# End of file
