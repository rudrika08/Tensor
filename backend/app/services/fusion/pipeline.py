"""
Multi-Modal Fusion Pipeline — Phase 5
Combines vision + geo + fraud into cash flow estimate with confidence intervals.
"""
import logging
from app.services.fusion.scorer import compute_daily_sales
from app.services.fusion.uncertainty_estimator import compute_confidence_interval
from app.services.fusion.margin_calculator import compute_monthly_income
from app.services.fusion.explainer import compute_shap_factors

logger = logging.getLogger(__name__)


def run_fusion_pipeline(
    vision_signals: dict,
    geo_signals: dict,
    fraud_assessment: dict,
) -> dict:
    try:
        # Point estimate
        sales_point, weights = compute_daily_sales(vision_signals, geo_signals)

        # Confidence interval (quantile regression)
        ci = compute_confidence_interval(vision_signals, geo_signals, fraud_assessment, sales_point)

        # Monthly income after margin
        monthly = compute_monthly_income(sales_point, ci, vision_signals)

        # SHAP-style factor explanation
        shap_factors = compute_shap_factors(weights, vision_signals, geo_signals)

        return {
            "daily_sales_point": round(sales_point, 0),
            "daily_sales_low": round(ci["low"], 0),
            "daily_sales_high": round(ci["high"], 0),
            "confidence_score": round(ci["confidence"], 3),
            "monthly_income_point": round(monthly["income_point"], 0),
            "monthly_income_low": round(monthly["income_low"], 0),
            "monthly_income_high": round(monthly["income_high"], 0),
            "blended_margin": round(monthly["blended_margin"], 4),
            "store_size_tier": vision_signals.get("store_size_tier", "medium"),
            "base_sales": round(weights["base"], 0),
            "weights_applied": {k: round(v, 3) for k, v in weights.items() if k != "base"},
            "shap_factors": shap_factors,
        }

    except Exception as e:
        logger.exception(f"Fusion pipeline error: {e}")
        return {
            "daily_sales_point": 12000,
            "daily_sales_low": 8000,
            "daily_sales_high": 18000,
            "confidence_score": 0.3,
            "monthly_income_point": 24000,
            "monthly_income_low": 16000,
            "monthly_income_high": 36000,
            "blended_margin": 0.12,
            "store_size_tier": "medium",
            "error": str(e),
        }
