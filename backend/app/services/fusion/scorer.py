"""
Weighted sales estimation formula.
Estimated Daily Sales = Base × SDI_weight × SKU_weight × GeoScore_weight × CompetitionFactor
"""
from typing import Tuple

# Base sales by store size tier (₹/day — midpoints from CRISIL/RBI data)
BASE_SALES = {
    "small":  4500.0,   # <100 sqft: ₹3,000–6,000
    "medium": 14000.0,  # 100–300 sqft: ₹8,000–20,000
    "large":  40000.0,  # >300 sqft: ₹20,000–60,000
}


def sdi_to_weight(sdi: float) -> float:
    """Map SDI [0,1] → weight [0.6, 1.4]."""
    return 0.6 + sdi * 0.8


def sku_to_weight(sku: int) -> float:
    """Map SKU diversity [0,30+] → weight [0.7, 1.3]."""
    normalized = min(sku / 20.0, 1.0)
    return 0.7 + normalized * 0.6


def geo_to_weight(geo_score: float) -> float:
    """Map geo score [0,100] → weight [0.5, 1.6]."""
    normalized = geo_score / 100.0
    return 0.5 + normalized * 1.1


def compute_daily_sales(vision: dict, geo: dict) -> Tuple[float, dict]:
    """
    Returns (point_estimate, weights_dict)
    """
    size_tier = vision.get("store_size_tier", "medium")
    base = BASE_SALES.get(size_tier, BASE_SALES["medium"])

    sdi = vision.get("sdi", 0.5)
    sku = vision.get("sku_diversity", 10)
    geo_score = geo.get("geo_score", 50.0)
    competition_factor = geo.get("competition_factor", 1.0)

    sdi_w = sdi_to_weight(sdi)
    sku_w = sku_to_weight(sku)
    geo_w = geo_to_weight(geo_score)

    point_estimate = base * sdi_w * sku_w * geo_w * competition_factor

    weights = {
        "base": base,
        "sdi_weight": sdi_w,
        "sku_weight": sku_w,
        "geo_weight": geo_w,
        "competition_factor": competition_factor,
    }

    return float(point_estimate), weights
