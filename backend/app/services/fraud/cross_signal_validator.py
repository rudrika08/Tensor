"""
Cross-Signal Economic Rule Engine — Phase 4
Applies business logic rules across vision + geo signals.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def check_cross_signals(
    vision_signals: dict,
    geo_signals: dict,
    years_in_operation: Optional[int],
    claimed_floor_area: Optional[float],
) -> dict:
    flags = []
    details = {}

    sdi = vision_signals.get("sdi", 0.5)
    sku_diversity = vision_signals.get("sku_diversity", 10)
    inventory_value = vision_signals.get("inventory_value_est", 50000)
    store_size = vision_signals.get("store_size_tier", "medium")
    floor_area_est = vision_signals.get("floor_area_est_sqft", 150)
    category_mix = vision_signals.get("category_mix", {})

    footfall = geo_signals.get("footfall_proxy_score", 50)
    road_type = geo_signals.get("road_type", "residential")
    catchment = geo_signals.get("catchment_tier", "urban_sparse")
    competition = geo_signals.get("competition_count", 3)

    # ── Rule 1: High inventory + low footfall rural ───────────────────────
    if (inventory_value > 150000 and footfall < 30
            and catchment in ("rural", "peri_urban")
            and road_type in ("residential", "service", "unclassified")):
        flags.append("inventory_footfall_mismatch")
        details["rule1"] = (
            f"High inventory (₹{inventory_value:,.0f}) in low-footfall rural area "
            f"(footfall={footfall}, road={road_type})"
        )

    # ── Rule 2: Overfull shelves + low SKU diversity ─────────────────────
    if sdi > 0.88 and sku_diversity < 6:
        flags.append("possible_inspection_restocking")
        details["rule2"] = (
            f"Very high SDI ({sdi}) with low SKU diversity ({sku_diversity}). "
            "Possible pre-inspection restocking with bulk staples."
        )

    # ── Rule 3: New-looking store + claimed old age ───────────────────────
    if years_in_operation and years_in_operation >= 10:
        # New-looking proxy: high brightness in HSV (not computed here, use SDI + category proxy)
        tobacco_weight = category_mix.get("tobacco", 0)
        fmcg_weight = category_mix.get("FMCG", 0)
        if fmcg_weight > 0.5 and tobacco_weight < 0.05:
            # Modern FMCG-heavy store claims >10 years — unusual for traditional kirana
            flags.append("age_claim_mismatch")
            details["rule3"] = (
                f"Store claims {years_in_operation} years but shows modern FMCG-heavy "
                f"profile ({fmcg_weight:.0%} FMCG), unusual for older kirana stores."
            )

    # ── Rule 4: High category diversity + very small floor area ──────────
    if sku_diversity > 18 and (store_size == "small" or floor_area_est < 80):
        flags.append("space_category_inconsistency")
        details["rule4"] = (
            f"High SKU diversity ({sku_diversity} categories) but estimated floor area "
            f"is only {floor_area_est:.0f} sqft. Space-to-inventory ratio is implausible."
        )

    # ── Rule 5: Oversupply in saturated market ───────────────────────────
    if sdi > 0.90 and competition > 8:
        flags.append("oversupply_high_competition")
        details["rule5"] = (
            f"Full shelves (SDI={sdi}) despite {competition} competing stores within 300m. "
            "Margin compression risk is high."
        )

    # ── Rule 6: Claimed area vs estimated area mismatch ─────────────────
    if claimed_floor_area and floor_area_est:
        ratio = claimed_floor_area / (floor_area_est + 1e-6)
        if ratio > 2.5 or ratio < 0.3:
            flags.append("floor_area_claim_mismatch")
            details["rule6"] = (
                f"Claimed floor area {claimed_floor_area:.0f} sqft vs estimated "
                f"{floor_area_est:.0f} sqft (ratio {ratio:.1f}x)"
            )

    return {"flags": flags, "details": details}
