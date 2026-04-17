"""
Competition Density Index.
Queries OpenStreetMap Overpass API for nearby kirana/convenience stores.
100% free — no API key needed.
"""
import logging
import requests
from app.services.geo.catchment import haversine_km

logger = logging.getLogger(__name__)


def query_nearby_stores(lat: float, lon: float, radius_m: int = 300) -> list:
    """Query OSM for nearby retail stores."""
    query = f"""
    [out:json][timeout:15];
    (
      node["shop"~"convenience|supermarket|grocery|kirana|general"](around:{radius_m},{lat},{lon});
      node["amenity"="marketplace"](around:{radius_m},{lat},{lon});
    );
    out body;
    """
    try:
        resp = requests.post(
            "https://overpass-api.de/api/interpreter",
            data={"data": query},
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json().get("elements", [])
    except Exception as e:
        logger.warning(f"Competition query failed: {e}")
        return []


def compute_competition(lat: float, lon: float) -> dict:
    """
    Returns competition density index and scoring factor.
    """
    stores = query_nearby_stores(lat, lon, radius_m=300)
    count = len(stores)

    # Scoring per implementation plan:
    # 0–1 stores → 0.9 (monopoly, less proven demand)
    # 2–4 stores → 1.0 (healthy competition = demand signal)
    # 5–8 stores → 0.9 (slight margin pressure)
    # >8 stores  → 0.8 (high margin compression)
    if count == 0:
        factor = 0.85
        label = "monopoly"
    elif count <= 1:
        factor = 0.90
        label = "very_low"
    elif count <= 4:
        factor = 1.00
        label = "healthy"
    elif count <= 8:
        factor = 0.90
        label = "high"
    else:
        factor = 0.80
        label = "saturated"

    nearby = []
    for s in stores[:10]:
        tags = s.get("tags", {})
        s_lat = s.get("lat", lat)
        s_lon = s.get("lon", lon)
        dist = haversine_km(lat, lon, s_lat, s_lon) * 1000
        nearby.append({
            "name": tags.get("name", "Unknown Store"),
            "type": tags.get("shop", "convenience"),
            "distance_m": round(dist),
        })

    return {
        "competition_count": count,
        "competition_factor": factor,
        "competition_label": label,
        "nearby_stores": nearby,
    }
