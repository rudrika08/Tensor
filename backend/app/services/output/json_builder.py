"""
JSON output builder — Phase 6
"""
from datetime import datetime


def build_output(submission, vision: dict, geo: dict, fraud: dict, cash_flow: dict) -> dict:
    return {
        "submission_id": str(submission.id),
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "store": {
            "name": submission.store_name,
            "latitude": submission.latitude,
            "longitude": submission.longitude,
            "years_in_operation": submission.years_in_operation,
            "claimed_floor_area_sqft": submission.claimed_floor_area_sqft,
            "monthly_rent": submission.monthly_rent,
        },
        "vision_signals": {
            "shelf_density_index": vision.get("sdi"),
            "sku_diversity": vision.get("sku_diversity"),
            "detected_products": vision.get("detected_product_count"),
            "dominant_category": vision.get("dominant_category"),
            "category_mix": vision.get("category_mix"),
            "inventory_value_est_inr": vision.get("inventory_value_est"),
            "store_size_tier": vision.get("store_size_tier"),
            "floor_area_est_sqft": vision.get("floor_area_est_sqft"),
        },
        "geo_signals": {
            "catchment_tier": geo.get("catchment_tier"),
            "population_500m": geo.get("population_500m"),
            "footfall_proxy_score": geo.get("footfall_proxy_score"),
            "road_type": geo.get("road_type"),
            "poi_count": geo.get("poi_count"),
            "competition_count": geo.get("competition_count"),
            "competition_label": geo.get("competition_factor"),
            "geo_score": geo.get("geo_score"),
        },
        "fraud_assessment": {
            "risk_level": fraud.get("risk_level"),
            "flag_count": fraud.get("flag_count"),
            "flags": fraud.get("flags"),
            "confidence": fraud.get("confidence"),
        },
        "cash_flow_estimate": {
            "daily_sales_range_inr": [
                cash_flow.get("daily_sales_low"),
                cash_flow.get("daily_sales_high"),
            ],
            "daily_sales_point_inr": cash_flow.get("daily_sales_point"),
            "monthly_income_range_inr": [
                cash_flow.get("monthly_income_low"),
                cash_flow.get("monthly_income_high"),
            ],
            "monthly_income_point_inr": cash_flow.get("monthly_income_point"),
            "confidence_score": cash_flow.get("confidence_score"),
            "blended_margin_pct": round((cash_flow.get("blended_margin", 0.12)) * 100, 1),
        },
        "key_factors": cash_flow.get("shap_factors", {}),
    }
