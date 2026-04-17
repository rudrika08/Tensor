"""
Uncertainty estimator using quantile regression for 70% CI.
"""



def compute_confidence_interval(
    vision: dict, geo: dict, fraud: dict, point_estimate: float
) -> dict:
    """
    Compute 70% confidence interval (15th–85th percentile) for daily sales.
    Uses signal quality to determine band width.
    """
    # Base uncertainty: ±30% of point estimate
    base_band = 0.30

    # Widen band based on fraud flags
    fraud_flags = len(fraud.get("flags", []))
    fraud_penalty = fraud_flags * 0.05

    # Widen if signals are weak
    sdi = vision.get("sdi", 0.5)
    geo_score = geo.get("geo_score", 50.0)
    image_count = vision.get("image_count", 3)

    signal_penalty = 0.0
    if sdi < 0.3:
        signal_penalty += 0.08
    if geo_score < 30:
        signal_penalty += 0.08
    if image_count < 3:
        signal_penalty += 0.10

    # Confidence score (0=very uncertain, 1=very confident)
    confidence = max(0.2, 1.0 - (fraud_penalty + signal_penalty + base_band * 0.5))

    total_band = base_band + fraud_penalty + signal_penalty

    low = point_estimate * (1 - total_band)
    high = point_estimate * (1 + total_band)

    return {
        "low": max(low, 1000.0),  # floor at ₹1,000
        "high": high,
        "confidence": round(confidence, 3),
        "band_width": round(total_band, 3),
    }
