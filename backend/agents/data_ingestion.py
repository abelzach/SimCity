"""
Agent 1: Data Ingestion Agent
Fetches and prepares Kochi's road network from OpenStreetMap.
"""
import logging
from typing import Dict, Any

from core.city_model import fetch_city_graph, graph_to_state_dict, compute_baseline_metrics
from core.state import SimCityState

logger = logging.getLogger(__name__)


def data_ingestion_agent(state: SimCityState) -> Dict[str, Any]:
    """Fetch Kochi road network and compute baseline graph structure."""
    logger.info("Data Ingestion Agent: starting")

    try:
        G = fetch_city_graph(state["city_name"])
        graph_data = graph_to_state_dict(G)
        baseline_metrics = compute_baseline_metrics(graph_data)

        log_msg = (
            f"Data Ingestion complete: {graph_data['node_count']} nodes, "
            f"{graph_data['edge_count']} road segments loaded for {state['city_name']}"
        )
        logger.info(log_msg)

        return {
            "city_graph_data": graph_data,
            "baseline_metrics": baseline_metrics,
            "agent_logs": state.get("agent_logs", []) + [log_msg],
            "status": "running",
        }
    except Exception as e:
        err = f"Data Ingestion Agent error: {e}"
        logger.error(err)
        return {
            "status": "error",
            "error": err,
            "agent_logs": state.get("agent_logs", []) + [err],
        }
