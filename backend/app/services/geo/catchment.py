"""
Catchment Density Score.
Uses H3 hexagonal indexing + WorldPop-style population tiers.
Falls back to coordinate-based heuristics when raster data unavailable.
"""
import logging
import math

logger = logging.getLogger(__name__)

# India major urban center bounding boxes for tier classification heuristic
URBAN_DENSE_CITIES = [
    # (center_lat, center_lon, radius_km, name)
    (19.0760, 72.8777, 25, "Mumbai"),
    (28.6139, 77.2090, 30, "Delhi"),
    (12.9716, 77.5946, 20, "Bangalore"),
    (22.5726, 88.3639, 20, "Kolkata"),
    (17.3850, 78.4867, 20, "Hyderabad"),
    (13.0827, 80.2707, 20, "Chennai"),
    (23.0225, 72.5714, 15, "Ahmedabad"),
    (18.5204, 73.8567, 15, "Pune"),
    (26.8467, 80.9462, 15, "Lucknow"),
    (22.7196, 75.8577, 10, "Indore"),
]


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def classify_india_catchment(lat: float, lon: float) -> dict:
    """
    Heuristic catchment tier for India coordinates.
    In production: replace with WorldPop raster query via rasterio.
    """
    for city_lat, city_lon, radius_km, city_name in URBAN_DENSE_CITIES:
        dist = haversine_km(lat, lon, city_lat, city_lon)
        if dist <= radius_km * 0.4:
            return {"tier": "urban_dense", "city": city_name, "dist_km": round(dist, 1)}
        if dist <= radius_km:
            return {"tier": "urban_sparse", "city": city_name, "dist_km": round(dist, 1)}
        if dist <= radius_km * 1.8:
            return {"tier": "peri_urban", "city": city_name, "dist_km": round(dist, 1)}

    return {"tier": "rural", "city": None, "dist_km": None}


TIER_CONFIG = {
    "urban_dense":  {"population_500m": 15000, "density_score": 90.0},
    "urban_sparse": {"population_500m": 6000,  "density_score": 65.0},
    "peri_urban":   {"population_500m": 2500,  "density_score": 40.0},
    "rural":        {"population_500m": 800,   "density_score": 20.0},
}


def compute_catchment(lat: float, lon: float) -> dict:
    """
    Returns catchment signals for a GPS coordinate.
    """
    try:
        import h3
        # H3 resolution 8 = ~0.7km² hex, resolution 9 = ~0.1km²
        h3_index = h3.latlng_to_cell(lat, lon, 8)
        neighbors = h3.grid_disk(h3_index, 1)  # 7-cell neighborhood ~500m radius
        hex_count = len(neighbors)
    except ImportError:
        h3_index = None
        hex_count = 7

    region = classify_india_catchment(lat, lon)
    tier = region["tier"]
    config = TIER_CONFIG.get(tier, TIER_CONFIG["urban_sparse"])

    return {
        "tier": tier,
        "city": region.get("city"),
        "h3_index": h3_index,
        "population_500m": config["population_500m"],
        "density_score": config["density_score"],
    }
