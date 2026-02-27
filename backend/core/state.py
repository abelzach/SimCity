from typing import TypedDict, Optional, List, Dict, Any


class SimCityState(TypedDict):
    city_name: str
    policy_description: str
    policy_type: str  # road_closure | new_route | signal_timing | transit_add
    city_graph_data: Dict[str, Any]  # Serialized node/edge data + GeoJSON
    baseline_metrics: Dict[str, Any]
    modified_graph_data: Dict[str, Any]
    citizen_profiles: List[Dict[str, Any]]
    simulation_results: Dict[str, Any]
    impact_scores: Dict[str, Any]
    recommendations: str
    agent_logs: List[str]
    status: str  # running | completed | error
    error: Optional[str]
