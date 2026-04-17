"""
Margin calculator — blends product-category-aware margin assumptions.
"""

# Net margin by category (from plan)
CATEGORY_MARGINS = {
    "staples": 0.10,
    "FMCG": 0.175,
    "snacks": 0.215,
    "beverages": 0.15,
    "dairy": 0.08,
    "tobacco": 0.215,
    "personal_care": 0.20,
    "household": 0.15,
    "fresh_produce": 0.12,
}

WORKING_DAYS = 26  # per month


def compute_monthly_income(
    daily_sales_point: float,
    ci: dict,
    vision: dict,
) -> dict:
    category_mix = vision.get("category_mix", {"staples": 0.5, "FMCG": 0.3, "snacks": 0.2})

    # Blended margin weighted by category mix
    blended_margin = sum(
        CATEGORY_MARGINS.get(cat, 0.12) * weight
        for cat, weight in category_mix.items()
    )
    # Normalize in case weights don't sum to 1
    total_weight = sum(category_mix.values())
    if total_weight > 0:
        blended_margin /= total_weight

    income_point = daily_sales_point * WORKING_DAYS * blended_margin
    income_low = ci["low"] * WORKING_DAYS * blended_margin
    income_high = ci["high"] * WORKING_DAYS * blended_margin

    return {
        "income_point": income_point,
        "income_low": income_low,
        "income_high": income_high,
        "blended_margin": blended_margin,
        "working_days": WORKING_DAYS,
    }
