"""
Vision Pipeline Orchestrator — Phase 2
Chains: Preprocessor → YOLO Detector → CLIP Classifier → SAM Segmenter → MiDaS Depth
Returns a unified VisionSignals dict.
"""
import logging
import asyncio
from typing import List
from app.services.vision.preprocessor import preprocess_image
from app.services.vision.detector import compute_yolo_signals
from app.services.vision.clip_classifier import classify_categories
from app.services.vision.segmenter import compute_shelf_fill
from app.services.vision.depth_estimator import estimate_floor_area

logger = logging.getLogger(__name__)


async def run_vision_pipeline(image_paths: List[str], image_labels: List[str]) -> dict:
    """
    Run all vision services and return VisionSignals dict.
    """
    if not image_paths:
        return _empty_signals()

    shelf_paths = [p for p, l in zip(image_paths, image_labels) if l == "shelf"]
    exterior_paths = [p for p, l in zip(image_paths, image_labels) if l == "exterior"]
    all_paths = image_paths

    try:
        # Preprocess all images
        preprocessed = [preprocess_image(p) for p in all_paths]

        # Run detection, classification, segmentation, depth in parallel
        yolo_task = asyncio.to_thread(compute_yolo_signals, preprocessed, image_labels)
        clip_task = asyncio.to_thread(classify_categories, preprocessed)
        sam_task = asyncio.to_thread(compute_shelf_fill, [p for p, l in zip(preprocessed, image_labels) if l == "shelf"])
        depth_task = asyncio.to_thread(estimate_floor_area, exterior_paths or all_paths[:1])

        yolo_signals, category_mix, shelf_fill, floor_area = await asyncio.gather(
            yolo_task, clip_task, sam_task, depth_task
        )

        signals = {
            # Shelf Density Index
            "sdi": round(shelf_fill.get("avg_fill_ratio", yolo_signals.get("sdi", 0.5)), 3),
            "shelf_zone_count": shelf_fill.get("zone_count", 0),

            # SKU diversity
            "sku_diversity": yolo_signals.get("sku_diversity", 0),
            "detected_product_count": yolo_signals.get("product_count", 0),

            # Category mix from CLIP
            "category_mix": category_mix,
            "dominant_category": max(category_mix, key=category_mix.get) if category_mix else "unknown",

            # Inventory value estimate
            "inventory_value_est": yolo_signals.get("inventory_value_est", 0.0),

            # Store size
            "store_size_tier": floor_area.get("size_tier", "medium"),
            "floor_area_est_sqft": floor_area.get("floor_area_sqft", 150.0),

            # Quality metadata
            "image_count": len(all_paths),
            "shelf_image_count": len(shelf_paths),
            "exterior_image_count": len(exterior_paths),
        }

        logger.info(f"Vision signals: SDI={signals['sdi']}, SKU={signals['sku_diversity']}, tier={signals['store_size_tier']}")
        return signals

    except Exception as e:
        logger.exception(f"Vision pipeline error: {e}")
        return _empty_signals(error=str(e))


def _empty_signals(error: str = None) -> dict:
    return {
        "sdi": 0.5,
        "shelf_zone_count": 0,
        "sku_diversity": 5,
        "detected_product_count": 0,
        "category_mix": {"staples": 0.5, "FMCG": 0.3, "snacks": 0.2},
        "dominant_category": "staples",
        "inventory_value_est": 50000.0,
        "store_size_tier": "medium",
        "floor_area_est_sqft": 150.0,
        "image_count": 0,
        "shelf_image_count": 0,
        "exterior_image_count": 0,
        "error": error,
    }
