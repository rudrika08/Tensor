"""
SHAP-style factor explainer — maps weight contributions to human-readable factors.
"""


def compute_shap_factors(weights: dict, vision: dict, geo: dict) -> dict:
    """
    Compute percentage contribution of each factor to final estimate.
    """
    base = weights.get("base", 14000)
    sdi_w = weights.get("sdi_weight", 1.0)
    sku_w = weights.get("sku_weight", 1.0)
    geo_w = weights.get("geo_weight", 1.0)
    comp_f = weights.get("competition_factor", 1.0)

    total_multiplier = sdi_w * sku_w * geo_w * comp_f
    final = base * total_multiplier

    def pct_contribution(factor_val):
        return round((factor_val - 1.0) / (total_multiplier - 1.0 + 1e-6) * 100, 1) if total_multiplier != 1.0 else 0.0

    return {
        "shelf_density": {
            "value": round(vision.get("sdi", 0.5), 3),
            "weight": round(sdi_w, 3),
            "direction": "positive" if sdi_w >= 1.0 else "negative",
            "label": "Shelf fill level",
        },
        "sku_diversity": {
            "value": vision.get("sku_diversity", 10),
            "weight": round(sku_w, 3),
            "direction": "positive" if sku_w >= 1.0 else "negative",
            "label": "Product variety",
        },
        "location_footfall": {
            "value": round(geo.get("geo_score", 50), 1),
            "weight": round(geo_w, 3),
            "direction": "positive" if geo_w >= 1.0 else "negative",
            "label": "Location & footfall",
        },
        "competition": {
            "value": geo.get("competition_count", 3),
            "weight": round(comp_f, 3),
            "direction": "positive" if comp_f >= 1.0 else "negative",
            "label": "Competition density",
        },
    }
