import json
from collections import deque
from langgraph.graph import StateGraph, END
from state import AgentState, NewTrafficData
from nodes import (
    traffic_agent_node,
    routing_agent_node,
    safety_agent_node,
    communication_agent_node,
)

# ──────────────────────────────────────────────
# Conditional Edge: Safety check router
# ──────────────────────────────────────────────
def safety_check_router(state: AgentState) -> str:
    if not state["is_safe"]:
        print(f"\n🚨 SAFETY BLOCK: {state['rejection_reason']}")
        return "unsafe"
    return "safe"


# ──────────────────────────────────────────────
# Build the Graph
# ──────────────────────────────────────────────
def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("traffic_agent",       traffic_agent_node)
    graph.add_node("routing_agent",       routing_agent_node)
    graph.add_node("safety_agent",        safety_agent_node)
    graph.add_node("communication_agent", communication_agent_node)

    graph.set_entry_point("traffic_agent")
    graph.add_edge("traffic_agent", "routing_agent")
    graph.add_edge("routing_agent", "safety_agent")

    graph.add_conditional_edges(
        "safety_agent",
        safety_check_router,
        {
            "safe":   "communication_agent",
            "unsafe": END,
        }
    )

    graph.add_edge("communication_agent", END)

    return graph.compile()


# ──────────────────────────────────────────────
# Network Graph Builder from dataset edges
# ──────────────────────────────────────────────
def build_network(edges: list) -> dict:
    """
    Build adjacency map: { node: [(neighbor, edge_id, mean_speed), ...] }
    Only includes non-internal edges (no ':' prefix).
    """
    graph = {}
    for e in edges:
        eid = e["id"]
        if eid.startswith(":"):
            continue
        parts = eid.split("_")
        if len(parts) != 2:
            continue
        src, tgt = parts
        graph.setdefault(src, [])
        graph.setdefault(tgt, [])
        graph[src].append((tgt, eid, e.get("mean_speed", 20.0)))
    return graph


def bfs_all_paths(graph: dict, source: str, destination: str, max_depth: int = 8) -> list:
    """
    BFS to find ALL simple paths from source to destination.
    Returns list of paths, each path = list of edge_ids.
    """
    if source not in graph or destination not in graph:
        return []

    # queue entries: (current_node, path_of_edges, visited_nodes)
    queue = deque()
    queue.append((source, [], {source}))
    all_paths = []

    while queue:
        current, edge_path, visited = queue.popleft()

        if len(edge_path) > max_depth:
            continue

        if current == destination:
            if edge_path:  # skip zero-length path (source == dest)
                all_paths.append(edge_path)
            continue

        for neighbor, edge_id, speed in graph.get(current, []):
            if neighbor not in visited:
                queue.append((neighbor, edge_path + [edge_id], visited | {neighbor}))

    return all_paths


def path_congestion_score(path: list, edge_map: dict) -> float:
    """
    Lower score = better path.
    Score = average congestion penalty across edges in path.
    HIGH=3, MEDIUM=2, LOW=1  (weighted by path length)
    """
    penalty = {"HIGH": 3.0, "MEDIUM": 2.0, "LOW": 1.0}
    total = 0.0
    for eid in path:
        e = edge_map.get(eid, {})
        spd = e.get("mean_speed", 20.0)
        level = "HIGH" if spd < 5.0 else "MEDIUM" if spd < 12.0 else "LOW"
        total += penalty[level]
    return total / len(path) if path else 999.0


# ──────────────────────────────────────────────
# Load & Validate Sim Data  (network-aware)
# ──────────────────────────────────────────────
def load_sim_data(
    path: str = "dataset.json",
    source: str = None,
    destination: str = None,
    vehicle_index: int = None,
    step_index: int = -1,
) -> NewTrafficData:
    """
    Build a NewTrafficData object for any source→destination pair by:
      1. Finding ALL paths using BFS over the real edge network.
      2. Picking the best (lowest congestion) primary path.
      3. Picking the next-best as the detour/alternate route.
      4. Setting checked_edge to the most congested edge on the primary path.

    Falls back to vehicle_index-based loading if source/destination not given.
    """
    with open(path, "r") as f:
        raw_data = json.load(f)

    steps = raw_data.get("steps", [])
    if not steps:
        raise IndexError("No simulation steps found in the dataset.")

    latest_step = steps[step_index]
    vehicles    = latest_step.get("vehicles", [])
    all_edges   = latest_step.get("edges", [])

    # ── Legacy mode: vehicle_index given, no source/dest ──
    if source is None and destination is None and vehicle_index is not None:
        if not vehicles:
            raise IndexError("No vehicles found in the selected simulation step.")
        if vehicle_index >= len(vehicles):
            raise IndexError(
                f"Vehicle index {vehicle_index} out of range "
                f"({len(vehicles)} vehicles in step)."
            )
        target_vehicle = vehicles[vehicle_index]
        full_route     = target_vehicle["route"]
        current_road   = target_vehicle["road"]
        source         = full_route[0].split("_")[0]
        destination    = full_route[-1].split("_")[1]

        edge_info  = next((e for e in all_edges if e["id"] == current_road), None)
        density    = edge_info["occupancy"]  if edge_info else 0.0
        mean_speed = edge_info["mean_speed"] if edge_info else 20.0
        congestion = "HIGH" if mean_speed < 5.0 else "MEDIUM" if mean_speed < 12.0 else "LOW"

        return NewTrafficData(
            source=source,
            destination=destination,
            checked_edge=current_road,
            vehicles=len(vehicles),
            density=density,
            congestion_level=congestion,
            selected_route=full_route,
            timestamp=int(latest_step["time"]),
        )

    # ── Network-aware mode: compute paths from source → destination ──
    network   = build_network(all_edges)
    edge_map  = {e["id"]: e for e in all_edges if not e["id"].startswith(":")}
    all_paths = bfs_all_paths(network, source, destination)

    if not all_paths:
        raise ValueError(
            f"No path exists between '{source}' and '{destination}' "
            f"in the current road network."
        )

    def ensure_complete_path(path: list) -> list:
        """
        Guarantee every consecutive node pair in a path has its edge included.
        This fixes cases where BFS returns a path but an intermediate edge
        (like E_F which has 0 vehicles) gets dropped or missed.
        """
        if not path:
            return path

        # Reconstruct node sequence from edge list
        nodes = []
        for edge in path:
            parts = edge.split("_")
            if len(parts) == 2:
                if not nodes:
                    nodes.append(parts[0])
                nodes.append(parts[1])

        # Re-derive edges from consecutive node pairs,
        # looking up the real edge ID from edge_map
        complete = []
        for i in range(len(nodes) - 1):
            src_n, tgt_n = nodes[i], nodes[i + 1]
            fwd = f"{src_n}_{tgt_n}"
            rev = f"{tgt_n}_{src_n}"
            if fwd in edge_map:
                complete.append(fwd)
            elif rev in edge_map:
                complete.append(rev)
            else:
                # Edge not found — keep original to avoid data loss
                complete.append(fwd)
        return complete

    # Apply completeness check to every BFS path
    all_paths = [ensure_complete_path(p) for p in all_paths]

    # Sort paths by congestion score (best first)
    scored = sorted(all_paths, key=lambda p: path_congestion_score(p, edge_map))
    best_path   = scored[0]
    detour_path = scored[1] if len(scored) > 1 else best_path

    # Find the most congested edge on the best path (this is what agents analyze)
    def worst_edge(path):
        worst, worst_spd = path[0], 999.0
        for eid in path:
            spd = edge_map.get(eid, {}).get("mean_speed", 20.0)
            if spd < worst_spd:
                worst_spd = spd
                worst = eid
        return worst, worst_spd

    checked_edge, checked_speed = worst_edge(best_path)
    edge_info  = edge_map.get(checked_edge, {})
    density    = edge_info.get("occupancy", 0.0)
    mean_speed = edge_info.get("mean_speed", 20.0)
    congestion = "HIGH" if mean_speed < 5.0 else "MEDIUM" if mean_speed < 12.0 else "LOW"

    return NewTrafficData(
        source=source,
        destination=destination,
        checked_edge=checked_edge,
        vehicles=len(vehicles),
        density=density,
        congestion_level=congestion,
        selected_route=best_path,
        alternate_route=detour_path,
        timestamp=int(latest_step["time"]),
        all_paths=[p for p in scored],
    )


# ──────────────────────────────────────────────
# CLI Runner
# ──────────────────────────────────────────────
def run_pipeline():
    print("=" * 55)
    print("   🚦 TRAFFIC ROUTING & SAFETY AGENT PIPELINE")
    print("=" * 55)

    sim_data = load_sim_data(source="A", destination="D")

    initial_state: AgentState = {
        "sim_data":            sim_data,
        "traffic_status":      "",
        "proposed_route":      [],
        "explanation":         "",
        "is_safe":             True,
        "rejection_reason":    None,
        "final_communication": "",
    }

    app = build_graph()
    final_state = app.invoke(initial_state)

    print(f"\n  Source → Destination : {sim_data.source} → {sim_data.destination}")
    print(f"  Best Path            : {' → '.join(sim_data.selected_route)}")
    print(f"  Alternate Path       : {' → '.join(sim_data.alternate_route)}")
    print(f"  Checked Edge         : {sim_data.checked_edge}")
    print(f"  Congestion           : {sim_data.congestion_level}")
    print(f"  [Agent 1] Traffic    : {final_state['traffic_status']}")
    print(f"  [Agent 2] Route      : {final_state['proposed_route']}")
    print(f"  [Agent 2] Reason     : {final_state['explanation']}")
    print(f"  [Agent 3] Safe?      : {'✅ Yes' if final_state['is_safe'] else '🚨 No'}")
    if final_state.get("final_communication"):
        print(f"\n  🚗 DRIVER: {final_state['final_communication']}")
    print("=" * 55)


if __name__ == "__main__":
    run_pipeline()