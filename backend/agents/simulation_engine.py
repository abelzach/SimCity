"""
Agent 2: Simulation Engine Agent
Builds a baseline traffic model using the city graph.
Computes travel times, congestion levels, and flow distributions.
"""
import logging
import numpy as np
from typing import Dict, Any

from core.state import SimCityState

logger = logging.getLogger(__name__)

# Kochi zone centroids (approximate lat/lon for 5 major zones)
KOCHI_ZONES = {
    "Ernakulam_CBD": {"lat": 9.9816, "lon": 76.2999, "population": 120000, "trips_out": 45000},
    "Kakkanad_IT": {"lat": 10.0159, "lon": 76.3419, "population": 80000, "trips_out": 35000},
    "Fort_Kochi": {"lat": 9.9658, "lon": 76.2421, "population": 50000, "trips_out": 20000},
    "Edappally": {"lat": 10.0270, "lon": 76.3083, "population": 90000, "trips_out": 40000},
    "Tripunithura": {"lat": 9.9450, "lon": 76.3484, "population": 70000, "trips_out": 30000},
}


def simulation_engine_agent(state: SimCityState) -> Dict[str, Any]:
    """Run baseline traffic simulation on the city graph."""
    logger.info("Simulation Engine Agent: computing baseline traffic model")

    try:
        graph_data = state["city_graph_data"]
        edges = graph_data["edges"]

        # Compute zone-level O/D statistics
        total_trips = sum(z["trips_out"] for z in KOCHI_ZONES.values())
        avg_congestion = float(np.mean([e["congestion_ratio"] for e in edges.values()]))
        peak_congestion = float(np.max([e["congestion_ratio"] for e in edges.values()]))

        # Identify bottleneck road segments (top 10% by congestion)
        sorted_edges = sorted(edges.items(), key=lambda x: x[1]["congestion_ratio"], reverse=True)
        bottlenecks = [
            {
                "edge_id": eid,
                "name": edata.get("name") or edata.get("highway", "unknown road"),
                "congestion_ratio": round(edata["congestion_ratio"], 3),
                "flow": edata["baseline_flow"],
                "capacity": edata["capacity"],
            }
            for eid, edata in sorted_edges[:10]
        ]

        # Traffic distribution by road type
        highway_stats = {}
        for eid, edata in edges.items():
            hw = edata.get("highway", "unclassified")
            if isinstance(hw, list):
                hw = hw[0]
            if hw not in highway_stats:
                highway_stats[hw] = {"count": 0, "total_congestion": 0.0, "total_flow": 0}
            highway_stats[hw]["count"] += 1
            highway_stats[hw]["total_congestion"] += edata["congestion_ratio"]
            highway_stats[hw]["total_flow"] += edata["baseline_flow"]

        road_type_summary = {
            hw: {
                "count": stats["count"],
                "avg_congestion": round(stats["total_congestion"] / stats["count"], 3),
                "total_flow": stats["total_flow"],
            }
            for hw, stats in highway_stats.items()
        }

        simulation_data = {
            "zones": KOCHI_ZONES,
            "total_daily_trips": total_trips,
            "avg_network_congestion": round(avg_congestion, 3),
            "peak_congestion_ratio": round(peak_congestion, 3),
            "bottleneck_segments": bottlenecks,
            "road_type_summary": road_type_summary,
            "simulation_type": "baseline",
        }

        log_msg = (
            f"Simulation Engine: baseline computed. Avg congestion {avg_congestion:.1%}, "
            f"peak {peak_congestion:.1%}. {len(bottlenecks)} bottleneck segments identified."
        )
        logger.info(log_msg)

        return {
            "simulation_results": simulation_data,
            "agent_logs": state.get("agent_logs", []) + [log_msg],
            "status": "running",
        }
    except Exception as e:
        err = f"Simulation Engine Agent error: {e}"
        logger.error(err)
        return {
            "status": "error",
            "error": err,
            "agent_logs": state.get("agent_logs", []) + [err],
        }
