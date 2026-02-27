"""
FastAPI routes: REST endpoints + SSE streaming for real-time agent updates.
"""
import asyncio
import json
import logging
import uuid
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.city_model import fetch_city_graph, graph_to_geojson, compute_baseline_metrics, graph_to_state_dict
from workflow.graph import run_simulation_stream

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory job store (upgrade to Redis/DB for production)
_jobs: Dict[str, Dict[str, Any]] = {}

POLICY_PRESETS = [
    {
        "id": "pedestrianize_mg_road",
        "title": "Pedestrianize MG Road",
        "description": "Close MG Road (Mahatma Gandhi Road) in Ernakulam to motor vehicles and convert to a pedestrian-friendly zone with street furniture and local shops",
        "icon": "🚶",
        "category": "road_closure",
    },
    {
        "id": "brt_nh66",
        "title": "Add BRT on NH-66 Corridor",
        "description": "Introduce a Bus Rapid Transit (BRT) dedicated lane along NH-66 from Edappally to Tripunithura with new bus stops and real-time tracking",
        "icon": "🚌",
        "category": "new_route",
    },
    {
        "id": "signal_optimization",
        "title": "AI Signal Timing Optimization",
        "description": "Deploy adaptive traffic signal control at the 15 busiest intersections in Kochi to reduce red-light wait times by 30% during peak hours",
        "icon": "🚦",
        "category": "signal_timing",
    },
    {
        "id": "water_taxi_expansion",
        "title": "Expand Water Taxi Network",
        "description": "Add 8 new ferry routes connecting Fort Kochi, Ernakulam, Vypin, and Bolgatty Island to reduce road load across Vembanad backwaters",
        "icon": "⛴️",
        "category": "transit_add",
    },
]


class SimulateRequest(BaseModel):
    policy: str
    city: str = "Kochi, Kerala, India"


@router.get("/city/kochi")
async def get_kochi_geojson():
    """Return Kochi road network as GeoJSON for map rendering."""
    try:
        G = fetch_city_graph("Kochi, Kerala, India")
        geojson = graph_to_geojson(G)
        return geojson
    except Exception as e:
        logger.error(f"Error fetching city GeoJSON: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/city/kochi/metrics")
async def get_baseline_metrics():
    """Return baseline traffic metrics for Kochi."""
    try:
        G = fetch_city_graph("Kochi, Kerala, India")
        graph_data = graph_to_state_dict(G)
        metrics = compute_baseline_metrics(graph_data)
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/presets")
async def get_presets():
    """Return pre-built policy scenario presets."""
    return POLICY_PRESETS


@router.post("/simulate")
async def start_simulation(req: SimulateRequest):
    """Start a new simulation job. Returns job_id for status polling and SSE."""
    if not req.policy.strip():
        raise HTTPException(status_code=400, detail="Policy description cannot be empty")

    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "id": job_id,
        "policy": req.policy,
        "city": req.city,
        "status": "queued",
        "result": None,
    }
    logger.info(f"Simulation job created: {job_id}")
    return {"job_id": job_id, "status": "queued"}


@router.get("/simulate/{job_id}/stream")
async def stream_simulation(job_id: str):
    """SSE endpoint: streams real-time agent updates for a simulation job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = _jobs[job_id]
    policy = job["policy"]
    city = job["city"]

    async def event_generator():
        # State accumulator across stream events
        accumulated = {
            "baseline_metrics": {},
            "impact_scores": {},
            "citizen_profiles": [],
            "recommendations": "",
        }

        try:
            _jobs[job_id]["status"] = "running"
            async for event in run_simulation_stream(policy, city):
                # Accumulate data events
                if event.get("type") == "data":
                    key = event.get("key")
                    if key:
                        accumulated[key] = event.get("data")

                if event.get("type") == "complete":
                    _jobs[job_id]["status"] = "completed"
                    _jobs[job_id]["result"] = accumulated

                payload = json.dumps(event)
                yield f"data: {payload}\n\n"
                await asyncio.sleep(0)  # yield control to event loop

        except Exception as e:
            logger.error(f"Stream error for job {job_id}: {e}")
            _jobs[job_id]["status"] = "error"
            error_event = json.dumps({"type": "error", "message": str(e)})
            yield f"data: {error_event}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.get("/simulate/{job_id}/result")
async def get_simulation_result(job_id: str):
    """Return final simulation result for a completed job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = _jobs[job_id]
    if job["status"] not in ("completed", "error"):
        raise HTTPException(status_code=202, detail="Simulation still running")

    return job
