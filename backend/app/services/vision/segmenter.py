"""
Meta SAM — Shelf segmentation and fill ratio computation.
Falls back to edge-based heuristic when SAM weights unavailable.
"""
import logging
import cv2
import numpy as np
from typing import List
from app.core.config import settings

logger = logging.getLogger(__name__)

_sam_predictor = None


def _load_sam():
    global _sam_predictor
    if _sam_predictor is not None:
        return True
    try:
        from segment_anything import sam_model_registry, SamAutomaticMaskGenerator
        import torch
        from pathlib import Path

        checkpoint = settings.SAM_CHECKPOINT_PATH
        if not Path(checkpoint).exists():
            logger.warning(f"SAM checkpoint not found at {checkpoint}, using heuristic fallback")
            return False

        sam = sam_model_registry[settings.SAM_MODEL_TYPE](checkpoint=checkpoint)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        sam.to(device=device)
        _sam_predictor = SamAutomaticMaskGenerator(
            model=sam,
            points_per_side=16,
            pred_iou_thresh=0.86,
            stability_score_thresh=0.92,
        )
        logger.info(f"SAM loaded on {device}")
        return True
    except Exception as e:
        logger.warning(f"SAM not available: {e}")
        return False


def compute_shelf_fill(shelf_images: List[np.ndarray]) -> dict:
    """
    Compute shelf fill ratio using SAM segments.
    Returns: {avg_fill_ratio, zone_count, per_image_fills}
    """
    if not shelf_images:
        return {"avg_fill_ratio": 0.5, "zone_count": 0, "per_image_fills": []}

    if _load_sam():
        return _sam_fill(shelf_images)
    else:
        return _heuristic_fill(shelf_images)


def _sam_fill(shelf_images: List[np.ndarray]) -> dict:
    fills = []
    zone_count = 0
    for img in shelf_images:
        try:
            rgb = img[..., ::-1]  # BGR → RGB
            masks = _sam_predictor.generate(rgb)
            if not masks:
                fills.append(0.5)
                continue
            h, w = img.shape[:2]
            total_area = h * w
            filled_area = sum(m["area"] for m in masks)
            ratio = min(filled_area / total_area, 1.0)
            fills.append(ratio)
            zone_count += len(masks)
        except Exception as e:
            logger.warning(f"SAM inference error on image: {e}")
            fills.append(0.5)

    return {
        "avg_fill_ratio": round(float(np.mean(fills)), 3) if fills else 0.5,
        "zone_count": zone_count,
        "per_image_fills": [round(f, 3) for f in fills],
    }


def _heuristic_fill(shelf_images: List[np.ndarray]) -> dict:
    """
    Edge and texture density as proxy for shelf fill ratio.
    Dense edges + texture → full shelf.
    """
    fills = []
    for img in shelf_images:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = edges.sum() / (gray.shape[0] * gray.shape[1] * 255)
        # Normalize: 0.02→empty, 0.15→full
        fill = np.clip((edge_density - 0.02) / (0.15 - 0.02), 0.1, 0.95)
        fills.append(float(fill))

    return {
        "avg_fill_ratio": round(float(np.mean(fills)), 3) if fills else 0.5,
        "zone_count": len(fills),
        "per_image_fills": [round(f, 3) for f in fills],
        "method": "heuristic",
    }
