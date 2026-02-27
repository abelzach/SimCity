"""
LangGraph workflow: orchestrates all 6 agents in sequence.
Provides a streaming interface for real-time frontend updates.
"""
import logging
from typing import AsyncGenerator, Dict, Any

from langgraph.graph import StateGraph, END

from core.state import SimCityState
from core.city_model import graph_to_geojson, state_dict_to_graph
from agents.data_ingestion import data_ingestion_agent
from agents.simulation_engine import simulation_engine_agent
from agents.citizen_proxy import citizen_proxy_agent
from agents.policy_testing import policy_testing_agent
from agents.impact_analysis import impact_analysis_agent
from agents.recommendation import recommendation_agent

logger = logging.getLogger(__name__)


def _should_continue(state: SimCityState) -> str:
    """Route to END if there's an error."""
    if state.get("status") == "error":
        return END
    return "continue"


def build_workflow() -> StateGraph:
    """Build and compile the LangGraph multi-agent workflow."""
    workflow = StateGraph(SimCityState)

    # Register all agent nodes
    workflow.add_node("data_ingestion", data_ingestion_agent)
    workflow.add_node("simulation_engine", simulation_engine_agent)
    workflow.add_node("citizen_proxy", citizen_proxy_agent)
    workflow.add_node("policy_testing", policy_testing_agent)
    workflow.add_node("impact_analysis", impact_analysis_agent)
    workflow.add_node("recommendation", recommendation_agent)

    # Sequential flow with error check between each step
    workflow.set_entry_point("data_ingestion")

    workflow.add_conditional_edges(
        "data_ingestion",
        lambda s: END if s.get("status") == "error" else "simulation_engine",
        {END: END, "simulation_engine": "simulation_engine"},
    )
    workflow.add_conditional_edges(
        "simulation_engine",
        lambda s: END if s.get("status") == "error" else "citizen_proxy",
        {END: END, "citizen_proxy": "citizen_proxy"},
    )
    workflow.add_conditional_edges(
        "citizen_proxy",
        lambda s: END if s.get("status") == "error" else "policy_testing",
        {END: END, "policy_testing": "policy_testing"},
    )
    workflow.add_conditional_edges(
        "policy_testing",
        lambda s: END if s.get("status") == "error" else "impact_analysis",
        {END: END, "impact_analysis": "impact_analysis"},
    )
    workflow.add_conditional_edges(
        "impact_analysis",
        lambda s: END if s.get("status") == "error" else "recommendation",
        {END: END, "recommendation": "recommendation"},
    )
    workflow.add_edge("recommendation", END)

    return workflow.compile()


AGENT_NAMES = {
    "data_ingestion": "Data Ingestion",
    "simulation_engine": "Simulation Engine",
    "citizen_proxy": "Citizen Proxy",
    "policy_testing": "Policy Testing",
    "impact_analysis": "Impact Analysis",
    "recommendation": "Recommendation",
}

# Singleton compiled workflow
_compiled_workflow = None


def get_workflow():
    global _compiled_workflow
    if _compiled_workflow is None:
        _compiled_workflow = build_workflow()
    return _compiled_workflow


async def run_simulation_stream(
    policy: str,
    city: str = "Kochi, Kerala, India",
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Run the full simulation workflow and yield events for SSE streaming.
    Each event has: type, agent, message, data (partial state).
    """
    app = get_workflow()

    initial_state: SimCityState = {
        "city_name": city,
        "policy_description": policy,
        "policy_type": "",
        "city_graph_data": {},
        "baseline_metrics": {},
        "modified_graph_data": {},
        "citizen_profiles": [],
        "simulation_results": {},
        "impact_scores": {},
        "recommendations": "",
        "agent_logs": [],
        "status": "running",
        "error": None,
    }

    yield {
        "type": "start",
        "agent": "orchestrator",
        "message": f"Starting SimCity AI simulation for policy: '{policy}'",
    }

    # Stream agent-by-agent updates
    async for event in app.astream(initial_state, stream_mode="updates"):
        for node_name, node_output in event.items():
            if node_name == "__end__":
                continue

            agent_display = AGENT_NAMES.get(node_name, node_name)
            logs = node_output.get("agent_logs", [])
            last_log = logs[-1] if logs else f"{agent_display} completed"

            yield {
                "type": "agent_complete",
                "agent": node_name,
                "agent_display": agent_display,
                "message": last_log,
                "status": node_output.get("status", "running"),
            }

            # Yield partial results after key agents
            if node_name == "data_ingestion":
                yield {
                    "type": "data",
                    "key": "baseline_metrics",
                    "data": node_output.get("baseline_metrics", {}),
                }
            elif node_name == "policy_testing":
                # Convert modified graph data to GeoJSON for frontend
                modified_graph_data = node_output.get("modified_graph_data", {})
                if modified_graph_data:
                    try:
                        # Convert state dict back to NetworkX graph
                        G = state_dict_to_graph(modified_graph_data)
                        # Convert to GeoJSON
                        modified_geojson = graph_to_geojson(G)
                        yield {
                            "type": "data",
                            "key": "modified_graph_data",
                            "data": {"geojson": modified_geojson},
                        }
                    except Exception as e:
                        logger.error(f"Error converting modified graph to GeoJSON: {e}")
                        yield {
                            "type": "data",
                            "key": "modified_graph_data",
                            "data": {"geojson": None},
                        }
            elif node_name == "impact_analysis":
                yield {
                    "type": "data",
                    "key": "impact_scores",
                    "data": node_output.get("impact_scores", {}),
                }
            elif node_name == "citizen_proxy":
                yield {
                    "type": "data",
                    "key": "citizen_profiles",
                    "data": node_output.get("citizen_profiles", []),
                }
            elif node_name == "recommendation":
                yield {
                    "type": "data",
                    "key": "recommendations",
                    "data": node_output.get("recommendations", ""),
                }

    yield {"type": "complete", "message": "Simulation completed"}
