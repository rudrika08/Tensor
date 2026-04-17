"""
YOLOv8 Product Detection & Shelf Density Index computation.
Falls back to mock signals if model weights are not available.
"""
import logging
import numpy as np
from typing import List, Optional
from pathlib import Path
from app.core.config import settings

logger = logging.getLogger(__name__)

# Category → approximate median retail price (₹ per unit)
CATEGORY_UNIT_PRICES = {
    "staples": 45,
    "FMCG": 80,
    "snacks": 25,
    "beverages": 35,
    "dairy": 55,
    "tobacco": 120,
    "personal_care": 90,
    "household": 65,
    "fresh_produce": 20,
}

_model = None


def _load_model():
    global _model
    if _model is not None:
        return _model
    try:
        from ultralytics import YOLO
        model_path = settings.YOLO_MODEL_PATH
        if Path(model_path).exists():
            _model = YOLO(model_path)
        else:
            _model = YOLO("yolov8n.pt")  # Download nano for demo
        logger.info("YOLOv8 model loaded")
    except Exception as e:
        logger.warning(f"YOLOv8 not available, using mock signals: {e}")
        _model = None
    return _model


def compute_yolo_signals(preprocessed_images: List[np.ndarray], image_labels: List[str]) -> dict:
    """
    Run YOLOv8 inference and compute:
    - SDI (Shelf Density Index)
    - SKU diversity count
    - Inventory value estimate
    """
    model = _load_model()

    if model is None:
        return _mock_signals()

    try:
        all_boxes = []
        shelf_images = [img for img, lbl in zip(preprocessed_images, image_labels) if lbl == "shelf"]
        target_images = shelf_images if shelf_images else preprocessed_images

        results = model(target_images, verbose=False, conf=0.25)

        total_img_area = 0
        total_box_area = 0
        unique_classes = set()
        product_count = 0

        for r in results:
            if r.boxes is None:
                continue
            h, w = r.orig_shape
            img_area = h * w
            total_img_area += img_area

            for box in r.boxes:
                cls_id = int(box.cls[0])
                cls_name = model.names.get(cls_id, "product")
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                box_area = (x2 - x1) * (y2 - y1)
                total_box_area += box_area
                unique_classes.add(cls_name)
                product_count += 1

        sdi = min(total_box_area / max(total_img_area, 1), 1.0)
        sku_diversity = len(unique_classes)

        # Rough inventory value: product_count × avg unit price × fill assumption
        avg_price = sum(CATEGORY_UNIT_PRICES.values()) / len(CATEGORY_UNIT_PRICES)
        inventory_value_est = product_count * avg_price * 3.0  # ×3 depth factor

        return {
            "sdi": round(sdi, 3),
            "sku_diversity": sku_diversity,
            "product_count": product_count,
            "inventory_value_est": round(inventory_value_est, 2),
            "detected_classes": list(unique_classes),
        }

    except Exception as e:
        logger.exception(f"YOLO inference error: {e}")
        return _mock_signals()


def _mock_signals() -> dict:
    """Plausible mock when model is unavailable."""
    import random
    sdi = round(random.uniform(0.45, 0.85), 3)
    sku_div = random.randint(8, 20)
    count = random.randint(40, 200)
    return {
        "sdi": sdi,
        "sku_diversity": sku_div,
        "product_count": count,
        "inventory_value_est": round(count * 55 * 2.5, 2),
        "detected_classes": ["staples", "snacks", "beverages", "FMCG"],
        "mock": True,
    }
