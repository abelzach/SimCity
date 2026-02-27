"""
Agent 4: Policy Testing Agent
Parses the policy description, applies it to the city graph,
and runs post-policy traffic simulation.
"""
import logging
import json
import copy
import numpy as np
from typing import Dict, Any

from anthropic import Anthropic

from core.city_model import compute_baseline_metrics
from core.state import SimCityState

logger = logging.getLogger(__name__)


POLICY_EFFECTS = {
    "road_closure": {
        "description": "Roads are removed from the network",
        "congestion_multiplier_surrounding": 1.35,  # surrounding roads get +35% load
        "closed_road_flow": 0,
    },
    "new_route": {
        "description": "New bus/transit route added, reducing car dependency",
        "congestion_reduction_corridor": 0.75,  # corridor gets 25% less congestion
        "modal_shift_factor": 0.15,  # 15% of car trips shift to transit
    },
    "signal_timing": {
        "description": "Optimized traffic signals reduce intersection delays",
        "congestion_reduction_network": 0.90,  # 10% reduction network-wide
        "speed_improvement": 1.10,  # 10% faster travel
    },
    "transit_add": {
        "description": "New transit mode (BRT/ferry) added",
        "congestion_reduction_corridor": 0.70,
        "modal_shift_factor": 0.20,
    },
}


def _parse_policy_with_llm(policy: str, graph_data: Dict) -> Dict[str, Any]:
    """Use LLM to extract structured policy parameters."""
    client = Anthropic()

    # Sample road names from the graph for context
    edge_names = list(set(
        e.get("name", "") for e in list(graph_data["edges"].values())[:200]
        if e.get("name")
    ))[:20]

    prompt = f"""You are an urban policy analyst for Kochi, Kerala, India.

Parse this policy proposal and extract structured parameters:
"{policy}"

Known road names in Kochi (sample): {json.dumps(edge_names)}

Return a JSON object with these exact fields:
{{
  "policy_type": one of ["road_closure", "new_route", "signal_timing", "transit_add"],
  "affected_area": "brief description of geographic area affected",
  "affected_road_keywords": ["list", "of", "road", "name", "keywords", "to", "match"],
  "scope": "local" | "corridor" | "network-wide",
  "description_for_report": "one clear sentence describing the policy",
  "estimated_affected_edges_pct": number between 1 and 30 (% of road network affected)
}}

Return ONLY valid JSON, no other text."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.content[0].text.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content.strip())
    except Exception as e:
        logger.warning(f"Policy parsing LLM failed: {e}, using defaults")
        return {
            "policy_type": "road_closure",
            "affected_area": "Central Kochi",
            "affected_road_keywords": [],
            "scope": "local",
            "description_for_report": policy,
            "estimated_affected_edges_pct": 5,
        }


def _apply_policy_to_graph(
    graph_data: Dict[str, Any],
    policy_params: Dict[str, Any],
) -> Dict[str, Any]:
    """Apply policy effects to graph edges and return modified graph data."""
    modified = copy.deepcopy(graph_data)
    edges = modified["edges"]

    policy_type = policy_params.get("policy_type", "road_closure")
    keywords = [k.lower() for k in policy_params.get("affected_road_keywords", [])]
    affected_pct = policy_params.get("estimated_affected_edges_pct", 5) / 100
    scope = policy_params.get("scope", "local")

    total_edges = len(edges)
    target_count = max(1, int(total_edges * affected_pct))

    # Find edges matching keywords or randomly select if no keywords
    matching_edges = []
    for eid, edata in edges.items():
        name = str(edata.get("name", "")).lower()
        hw = str(edata.get("highway", "")).lower()
        if keywords and any(kw in name or kw in hw for kw in keywords):
            matching_edges.append(eid)

    # If not enough keyword matches, supplement with high-congestion edges
    if len(matching_edges) < target_count:
        sorted_by_congestion = sorted(
            [(eid, e["congestion_ratio"]) for eid, e in edges.items()
             if eid not in matching_edges],
            key=lambda x: x[1], reverse=True
        )
        supplement = [eid for eid, _ in sorted_by_congestion[:target_count - len(matching_edges)]]
        matching_edges.extend(supplement)

    primary_edges = set(matching_edges[:target_count])

    rng = np.random.default_rng(42)

    if policy_type == "road_closure":
        for eid in primary_edges:
            edges[eid]["congestion_ratio"] = 0.0
            edges[eid]["baseline_flow"] = 0
            edges[eid]["closed"] = True
        # Redistribute traffic to surrounding edges
        other_edges = [eid for eid in edges if eid not in primary_edges]
        spill_count = min(len(other_edges), target_count * 3)
        spill_edges = rng.choice(other_edges, size=spill_count, replace=False)
        for eid in spill_edges:
            edges[eid]["congestion_ratio"] = min(
                1.0, edges[eid]["congestion_ratio"] * POLICY_EFFECTS["road_closure"]["congestion_multiplier_surrounding"]
            )

    elif policy_type in ("new_route", "transit_add"):
        factor = POLICY_EFFECTS[policy_type]["congestion_reduction_corridor"]
        modal_shift = POLICY_EFFECTS[policy_type]["modal_shift_factor"]
        for eid in primary_edges:
            edges[eid]["congestion_ratio"] = max(0.1, edges[eid]["congestion_ratio"] * factor)
            edges[eid]["baseline_flow"] = int(edges[eid]["baseline_flow"] * (1 - modal_shift))
        if scope == "network-wide":
            for eid in edges:
                if eid not in primary_edges:
                    edges[eid]["congestion_ratio"] = max(
                        0.1, edges[eid]["congestion_ratio"] * 0.95
                    )

    elif policy_type == "signal_timing":
        factor = POLICY_EFFECTS["signal_timing"]["congestion_reduction_network"]
        for eid in edges:
            edges[eid]["congestion_ratio"] = max(0.1, edges[eid]["congestion_ratio"] * factor)
            edges[eid]["travel_time"] = edges[eid]["travel_time"] / POLICY_EFFECTS["signal_timing"]["speed_improvement"]

    modified["policy_applied"] = policy_type
    modified["primary_affected_edges"] = list(primary_edges)
    return modified


def policy_testing_agent(state: SimCityState) -> Dict[str, Any]:
    """Parse policy, apply to graph, compute post-policy metrics."""
    logger.info("Policy Testing Agent: parsing and applying policy")

    try:
        graph_data = state["city_graph_data"]
        policy = state["policy_description"]

        # Parse policy with LLM
        policy_params = _parse_policy_with_llm(policy, graph_data)
        policy_type = policy_params.get("policy_type", "road_closure")

        # Apply policy to graph
        modified_graph = _apply_policy_to_graph(graph_data, policy_params)

        # Compute post-policy metrics
        post_metrics = compute_baseline_metrics(modified_graph)

        affected_count = len(modified_graph.get("primary_affected_edges", []))
        log_msg = (
            f"Policy Testing: applied '{policy_type}' to {affected_count} road segments. "
            f"Post-policy avg congestion: {post_metrics.get('avg_congestion_ratio', 0):.1%}"
        )
        logger.info(log_msg)

        return {
            "policy_type": policy_type,
            "modified_graph_data": modified_graph,
            "simulation_results": {
                **state.get("simulation_results", {}),
                "post_policy_metrics": post_metrics,
                "policy_params": policy_params,
                "affected_edge_count": affected_count,
            },
            "agent_logs": state.get("agent_logs", []) + [log_msg],
            "status": "running",
        }
    except Exception as e:
        err = f"Policy Testing Agent error: {e}"
        logger.error(err)
        return {
            "status": "error",
            "error": err,
            "agent_logs": state.get("agent_logs", []) + [err],
        }
