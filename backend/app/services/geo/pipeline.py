"""
Geo-Spatial Engine — Phase 3
Orchestrates: Catchment → Footfall → Competition
Returns unified GeoSignals dict.
"""
import logging
import asyncio

logger = logging.getLogger(__name__)


async def run_geo_pipeline(latitude: float, longitude: float) -> dict:
    try:
        from app.services.geo.catchment import compute_catchment
        from app.services.geo.footfall import compute_footfall
        from app.services.geo.competition import compute_competition

        catchment_task = asyncio.to_thread(compute_catchment, latitude, longitude)
        footfall_task = asyncio.to_thread(compute_footfall, latitude, longitude)
        competition_task = asyncio.to_thread(compute_competition, latitude, longitude)

        catchment, footfall, competition = await asyncio.gather(
            catchment_task, footfall_task, competition_task
        )

        # Composite geo score (0–100)
        geo_score = round(
            (footfall["footfall_proxy_score"] * 0.5) +
            (catchment["density_score"] * 0.3) +
            (competition["competition_factor"] * 100 * 0.2),
            1
        )

        return {
            # Catchment
            "catchment_tier": catchment["tier"],
            "population_500m": catchment["population_500m"],
            "density_score": catchment["density_score"],

            # Footfall
            "footfall_proxy_score": footfall["footfall_proxy_score"],
            "poi_count": footfall["poi_count"],
            "poi_breakdown": footfall["poi_breakdown"],
            "road_type": footfall["road_type"],
            "road_multiplier": footfall["road_multiplier"],

            # Competition
            "competition_count": competition["competition_count"],
            "competition_factor": competition["competition_factor"],
            "nearby_stores": competition.get("nearby_stores", []),

            # Composite
            "geo_score": geo_score,
        }

    except Exception as e:
        logger.exception(f"Geo pipeline error: {e}")
        return _default_geo()


def _default_geo() -> dict:
    return {
        "catchment_tier": "urban_sparse",
        "population_500m": 5000,
        "density_score": 50.0,
        "footfall_proxy_score": 50.0,
        "poi_count": 5,
        "poi_breakdown": {},
        "road_type": "local",
        "road_multiplier": 1.0,
        "competition_count": 3,
        "competition_factor": 1.0,
        "nearby_stores": [],
        "geo_score": 50.0,
        "error": "geo_pipeline_fallback",
    }
