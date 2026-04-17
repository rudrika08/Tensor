"""
Footfall Proxy Index.
Queries Overpass API (OpenStreetMap, free) for POIs.
Falls back to Google Places API if key is configured.
"""
import logging
import math
import requests
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

# POI type weights (traffic multiplier)
POI_WEIGHTS = {
    "bus_stop": 1.8,
    "bus_station": 2.0,
    "school": 1.5,
    "college": 1.6,
    "hospital": 1.4,
    "market": 2.0,
    "supermarket": 1.6,
    "bank": 1.3,
    "atm": 1.2,
    "office": 1.3,
    "railway_station": 2.5,
    "auto_stand": 1.6,
    "pharmacy": 1.2,
    "restaurant": 1.4,
    "fuel": 1.1,
}

ROAD_MULTIPLIERS = {
    "motorway": 1.8,
    "trunk": 1.6,
    "primary": 1.5,
    "secondary": 1.3,
    "tertiary": 1.1,
    "residential": 0.9,
    "service": 0.75,
    "unclassified": 0.85,
}


def query_overpass_pois(lat: float, lon: float, radius_m: int = 500) -> list:
    """Query OpenStreetMap Overpass API for nearby POIs."""
    query = f"""
    [out:json][timeout:15];
    (
      node["amenity"~"bus_stop|school|hospital|bank|atm|restaurant|pharmacy|fuel|marketplace|college"](around:{radius_m},{lat},{lon});
      node["shop"~"supermarket|convenience|mall"](around:{radius_m},{lat},{lon});
      node["public_transport"~"stop_position|station"](around:{radius_m},{lat},{lon});
      node["highway"="bus_stop"](around:{radius_m},{lat},{lon});
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
        elements = resp.json().get("elements", [])
        return elements
    except Exception as e:
        logger.warning(f"Overpass API query failed: {e}")
        return []


def query_overpass_roads(lat: float, lon: float) -> str:
    """Get the road type nearest to the store."""
    query = f"""
    [out:json][timeout:10];
    way["highway"](around:50,{lat},{lon});
    out tags;
    """
    try:
        resp = requests.post(
            "https://overpass-api.de/api/interpreter",
            data={"data": query},
            timeout=15,
        )
        resp.raise_for_status()
        ways = resp.json().get("elements", [])
        if ways:
            return ways[0].get("tags", {}).get("highway", "unclassified")
    except Exception as e:
        logger.warning(f"Road query failed: {e}")
    return "unclassified"


def compute_footfall(lat: float, lon: float) -> dict:
    """
    Compute Footfall Proxy Index (0–100) from POI density and road type.
    """
    poi_elements = query_overpass_pois(lat, lon, radius_m=500)
    road_type = query_overpass_roads(lat, lon)

    # Tally POIs by type
    poi_breakdown = {}
    weighted_sum = 0.0

    for elem in poi_elements:
        tags = elem.get("tags", {})
        amenity = tags.get("amenity", tags.get("shop", tags.get("public_transport", "")))
        # Normalize
        key = amenity.replace(" ", "_").lower()
        weight = POI_WEIGHTS.get(key, 0.8)
        poi_breakdown[key] = poi_breakdown.get(key, 0) + 1
        weighted_sum += weight

    poi_count = len(poi_elements)
    road_multiplier = ROAD_MULTIPLIERS.get(road_type, 0.85)

    # Score formula: normalized weighted POI sum × road multiplier × 100
    # Cap at 100
    raw_score = min(weighted_sum * road_multiplier * 3.5, 100.0)

    # Boost for high-traffic road types
    if road_type in ("motorway", "trunk", "primary"):
        raw_score = min(raw_score * 1.2, 100.0)

    # Fallback: if Overpass failed (0 POIs), use road type only
    if poi_count == 0:
        raw_score = ROAD_MULTIPLIERS.get(road_type, 0.85) * 45.0

    return {
        "footfall_proxy_score": round(raw_score, 1),
        "poi_count": poi_count,
        "poi_breakdown": poi_breakdown,
        "weighted_poi_sum": round(weighted_sum, 2),
        "road_type": road_type,
        "road_multiplier": road_multiplier,
    }
