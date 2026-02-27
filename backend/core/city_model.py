"""
City model: fetches Kochi road network from OpenStreetMap via OSMnx,
builds a NetworkX graph with traffic attributes, and exports GeoJSON.
"""
import os
import json
import pickle
import logging
from pathlib import Path
from typing import Dict, Any, Tuple

import osmnx as ox
import networkx as nx
import numpy as np

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent.parent / "data"
CACHE_DIR.mkdir(exist_ok=True)

GRAPH_CACHE = CACHE_DIR / "kochi_graph.pkl"
GEOJSON_CACHE = CACHE_DIR / "kochi_geojson.json"


# Speed limits (km/h) by OSM highway type
SPEED_LIMITS = {
    "motorway": 100,
    "trunk": 80,
    "primary": 60,
    "secondary": 50,
    "tertiary": 40,
    "residential": 30,
    "unclassified": 30,
    "service": 20,
    "living_street": 15,
}

# Lane capacity (vehicles/hour) per lane by road type
CAPACITY_PER_LANE = {
    "motorway": 2000,
    "trunk": 1800,
    "primary": 1500,
    "secondary": 1200,
    "tertiary": 900,
    "residential": 600,
    "unclassified": 600,
    "service": 400,
    "living_street": 300,
}


def _enrich_graph(G: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """Add speed, capacity, and baseline traffic to each edge."""
    for u, v, key, data in G.edges(data=True, keys=True):
        highway = data.get("highway", "unclassified")
        if isinstance(highway, list):
            highway = highway[0]

        speed = SPEED_LIMITS.get(highway, 30)
        data["speed_kph"] = speed
        data["speed_ms"] = speed / 3.6

        lanes = data.get("lanes", 1)
        if isinstance(lanes, list):
            lanes = int(lanes[0])
        else:
            try:
                lanes = int(lanes)
            except (TypeError, ValueError):
                lanes = 1
        data["lanes"] = lanes

        capacity = CAPACITY_PER_LANE.get(highway, 600) * lanes
        data["capacity"] = capacity

        length = data.get("length", 50)
        travel_time = length / (speed / 3.6)
        data["travel_time"] = travel_time

        # Baseline traffic: random 40-80% of capacity (simulates peak hour)
        rng = np.random.default_rng(abs(hash(f"{u}-{v}-{key}")) % (2**32))
        load_factor = rng.uniform(0.4, 0.8)
        data["baseline_flow"] = int(capacity * load_factor)
        data["congestion_ratio"] = load_factor

    return G


def fetch_city_graph(city: str = "Kochi, Kerala, India", force_refresh: bool = False) -> nx.MultiDiGraph:
    """Fetch road network from OSM (cached locally after first fetch)."""
    if GRAPH_CACHE.exists() and not force_refresh:
        logger.info("Loading Kochi graph from cache...")
        with open(GRAPH_CACHE, "rb") as f:
            return pickle.load(f)

    logger.info(f"Fetching road network for {city} from OpenStreetMap...")
    G = ox.graph_from_place(city, network_type="drive", simplify=True)
    G = _enrich_graph(G)

    with open(GRAPH_CACHE, "wb") as f:
        pickle.dump(G, f)
    logger.info(f"Graph cached: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G


def graph_to_geojson(G: nx.MultiDiGraph, modified_edges: Dict = None) -> Dict[str, Any]:
    """Convert NetworkX graph to GeoJSON FeatureCollection for frontend map."""
    if GEOJSON_CACHE.exists() and modified_edges is None:
        with open(GEOJSON_CACHE) as f:
            return json.load(f)

    features = []

    # Add edges as LineString features
    for u, v, key, data in G.edges(data=True, keys=True):
        if "geometry" in data:
            coords = list(data["geometry"].coords)
        else:
            u_data = G.nodes[u]
            v_data = G.nodes[v]
            coords = [
                (u_data.get("x", 0), u_data.get("y", 0)),
                (v_data.get("x", 0), v_data.get("y", 0)),
            ]

        edge_id = f"{u}-{v}-{key}"
        congestion = data.get("congestion_ratio", 0.5)
        if modified_edges and edge_id in modified_edges:
            congestion = modified_edges[edge_id].get("congestion_ratio", congestion)
            is_modified = True
        else:
            is_modified = False

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [[c[0], c[1]] for c in coords],
            },
            "properties": {
                "edge_id": edge_id,
                "highway": data.get("highway", "unclassified"),
                "name": data.get("name", ""),
                "length": round(data.get("length", 0), 1),
                "speed_kph": data.get("speed_kph", 30),
                "capacity": data.get("capacity", 600),
                "baseline_flow": data.get("baseline_flow", 0),
                "congestion_ratio": round(congestion, 3),
                "congestion_level": _congestion_level(congestion),
                "is_modified": is_modified,
                "is_closed": modified_edges.get(edge_id, {}).get("closed", False) if modified_edges else False,
            },
        })

    geojson = {"type": "FeatureCollection", "features": features}

    if modified_edges is None:
        with open(GEOJSON_CACHE, "w") as f:
            json.dump(geojson, f)

    return geojson


def _congestion_level(ratio: float) -> str:
    if ratio < 0.4:
        return "free"
    elif ratio < 0.6:
        return "moderate"
    elif ratio < 0.8:
        return "heavy"
    else:
        return "severe"


def graph_to_state_dict(G: nx.MultiDiGraph) -> Dict[str, Any]:
    """Serialize graph to a lightweight dict for LangGraph state."""
    nodes = {}
    for node_id, data in G.nodes(data=True):
        nodes[node_id] = {
            "x": data.get("x", 0),
            "y": data.get("y", 0),
        }

    edges = {}
    for u, v, key, data in G.edges(data=True, keys=True):
        edge_id = f"{u}-{v}-{key}"
        edges[edge_id] = {
            "u": u,
            "v": v,
            "key": key,
            "length": data.get("length", 100),
            "highway": data.get("highway", "unclassified"),
            "name": data.get("name", ""),
            "capacity": data.get("capacity", 1000),
            "speed_kph": data.get("speed_kph", 50),
            "baseline_flow": data.get("baseline_flow", 500),
            "congestion_ratio": data.get("congestion_ratio", 0.5),
            "travel_time": data.get("travel_time", 2),
            "geometry": data.get("geometry"),
        }

    return {
        "nodes": nodes,
        "edges": edges,
        "node_count": G.number_of_nodes(),
        "edge_count": G.number_of_edges(),
    }


def state_dict_to_graph(graph_data: Dict[str, Any]) -> nx.MultiDiGraph:
    """Deserialize state dict back to NetworkX graph."""
    G = nx.MultiDiGraph()
    
    # Add nodes
    for node_id, data in graph_data.get("nodes", {}).items():
        G.add_node(node_id, **data)
    
    # Add edges
    for edge_id, data in graph_data.get("edges", {}).items():
        u = data["u"]
        v = data["v"]
        key = data["key"]
        edge_attrs = {
            "length": data.get("length", 100),
            "highway": data.get("highway", "unclassified"),
            "name": data.get("name", ""),
            "capacity": data.get("capacity", 1000),
            "speed_kph": data.get("speed_kph", 50),
            "baseline_flow": data.get("baseline_flow", 500),
            "congestion_ratio": data.get("congestion_ratio", 0.5),
            "travel_time": data.get("travel_time", 2),
        }
        if data.get("geometry"):
            edge_attrs["geometry"] = data["geometry"]
        
        G.add_edge(u, v, key=key, **edge_attrs)
    
    return G


def compute_baseline_metrics(graph_data: Dict[str, Any]) -> Dict[str, Any]:
    """Compute city-wide traffic metrics from graph state dict."""
    edges = graph_data["edges"]

    total_edges = len(edges)
    if total_edges == 0:
        return {}

    congestion_ratios = [e["congestion_ratio"] for e in edges.values()]
    travel_times = [e["travel_time"] for e in edges.values()]
    flows = [e["baseline_flow"] for e in edges.values()]
    capacities = [e["capacity"] for e in edges.values()]

    avg_congestion = float(np.mean(congestion_ratios))
    severe_count = sum(1 for r in congestion_ratios if r > 0.8)
    total_flow = sum(flows)

    # Simplified emissions: CO2 = flow * avg_length * emission_factor
    avg_length_km = float(np.mean([e["length"] for e in edges.values()])) / 1000
    emission_factor = 0.21  # kg CO2 per vehicle-km (avg Indian traffic mix)
    daily_co2_kg = total_flow * avg_length_km * emission_factor * 8  # 8 peak hours

    # Economic cost: INR 50/hour per vehicle for congestion delay
    delay_fraction = max(0, avg_congestion - 0.4)
    avg_travel_time_min = float(np.mean(travel_times)) / 60
    delay_time_min = avg_travel_time_min * delay_fraction
    economic_loss_inr = total_flow * (delay_time_min / 60) * 50 * 8

    return {
        "avg_congestion_ratio": round(avg_congestion, 3),
        "severe_congestion_pct": round(severe_count / total_edges * 100, 1),
        "avg_travel_time_min": round(avg_travel_time_min, 2),
        "total_vehicle_flow": total_flow,
        "daily_co2_kg": round(daily_co2_kg, 1),
        "economic_loss_inr_per_day": round(economic_loss_inr, 0),
        "total_edges": total_edges,
        "total_nodes": graph_data["node_count"],
    }
