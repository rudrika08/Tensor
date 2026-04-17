"""
MiDaS depth estimator — estimates store floor area from a single image.
Falls back to aspect-ratio heuristic when MiDaS is unavailable.
"""
import logging
import cv2
import numpy as np
from typing import List
from app.core.config import settings

logger = logging.getLogger(__name__)

_midas_model = None
_midas_transform = None


def _load_midas():
    global _midas_model, _midas_transform
    if _midas_model is not None:
        return True
    try:
        import torch
        midas = torch.hub.load("intel-isl/MiDaS", settings.MIDAS_MODEL_TYPE, trust_repo=True)
        transforms = torch.hub.load("intel-isl/MiDaS", "transforms", trust_repo=True)
        if settings.MIDAS_MODEL_TYPE in ("DPT_Large", "DPT_Hybrid"):
            _midas_transform = transforms.dpt_transform
        else:
            _midas_transform = transforms.small_transform
        device = "cuda" if torch.cuda.is_available() else "cpu"
        midas.to(device)
        midas.eval()
        _midas_model = midas
        logger.info(f"MiDaS loaded on {device}")
        return True
    except Exception as e:
        logger.warning(f"MiDaS not available: {e}")
        return False


def estimate_floor_area(image_paths: List[str]) -> dict:
    """
    Estimate store floor area (sqft) and classify into size tier.
    Uses first available image.
    """
    if not image_paths:
        return {"floor_area_sqft": 150.0, "size_tier": "medium", "method": "default"}

    img_path = image_paths[0]
    img = cv2.imread(img_path)
    if img is None:
        return {"floor_area_sqft": 150.0, "size_tier": "medium", "method": "default"}

    if _load_midas():
        return _midas_estimate(img)
    else:
        return _heuristic_estimate(img)


def _midas_estimate(img: np.ndarray) -> dict:
    try:
        import torch
        device = next(_midas_model.parameters()).device
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        input_batch = _midas_transform(rgb).to(device)

        with torch.no_grad():
            prediction = _midas_model(input_batch)
            prediction = torch.nn.functional.interpolate(
                prediction.unsqueeze(1),
                size=rgb.shape[:2],
                mode="bicubic",
                align_corners=False,
            ).squeeze()

        depth_map = prediction.cpu().numpy()
        # Estimate floor region: bottom 40% of image
        h = depth_map.shape[0]
        floor_region = depth_map[int(h * 0.6):, :]
        avg_floor_depth = float(np.median(floor_region))
        # Heuristic: deeper floor → larger store
        # Map median depth [0.1–0.9 normalized] → [50–500 sqft]
        norm_depth = np.clip(avg_floor_depth / (depth_map.max() + 1e-6), 0, 1)
        floor_area = 50 + norm_depth * 450

        return {
            "floor_area_sqft": round(float(floor_area), 1),
            "size_tier": _classify_tier(floor_area),
            "method": "midas",
        }
    except Exception as e:
        logger.exception(f"MiDaS inference error: {e}")
        return _heuristic_estimate(img)


def _heuristic_estimate(img: np.ndarray) -> dict:
    """
    Use image aspect ratio + vanishing point detection as proxy.
    Wider images with high ceiling suggest larger stores.
    """
    h, w = img.shape[:2]
    aspect = w / h
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Detect horizontal lines (shelves imply narrow store)
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=80, minLineLength=w // 4, maxLineGap=20)
    h_line_count = 0
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
            if angle < 15:
                h_line_count += 1

    # Many horizontal lines = shelf-heavy store = potentially smaller floor
    if h_line_count > 10:
        floor_area = 80.0
    elif aspect > 1.5:
        floor_area = 200.0
    else:
        floor_area = 150.0

    return {
        "floor_area_sqft": floor_area,
        "size_tier": _classify_tier(floor_area),
        "method": "heuristic",
        "horizontal_lines": h_line_count,
    }


def _classify_tier(sqft: float) -> str:
    if sqft < 100:
        return "small"
    elif sqft <= 300:
        return "medium"
    else:
        return "large"
