import argparse
import json
import sys
from graph import run_pipeline, load_sim_data, build_graph
from state import AgentState

def main():
    parser = argparse.ArgumentParser(
        description="🚦 Traffic Routing & Safety Agent - CLI Runner"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="dataset.json",
        help="Path to the SUMO simulation dataset JSON file (default: dataset.json)"
    )
    parser.add_argument(
        "--vehicle",
        type=int,
        default=0,
        help="Index of the vehicle to analyze from the last simulation step (default: 0)"
    )
    parser.add_argument(
        "--output",
        type=str,
        choices=["pretty", "json"],
        default="pretty",
        help="Output format: 'pretty' for human-readable, 'json' for machine-readable (default: pretty)"
    )
    parser.add_argument(
        "--step",
        type=int,
        default=-1,
        help="Simulation step index to analyze, -1 means latest (default: -1)"
    )

    args = parser.parse_args()

    # ── Load & validate data ──────────────────────────────────────
    print(f"📂 Loading dataset: {args.dataset}")
    print(f"🚗 Analyzing vehicle index: {args.vehicle}")
    print(f"⏱  Simulation step: {'latest' if args.step == -1 else args.step}\n")

    try:
        sim_data = load_sim_data(path=args.dataset, vehicle_index=args.vehicle, step_index=args.step)
    except FileNotFoundError:
        print(f"❌ ERROR: Dataset file '{args.dataset}' not found.")
        sys.exit(1)
    except IndexError as e:
        print(f"❌ ERROR: {e}")
        sys.exit(1)

    # ── Build initial state ───────────────────────────────────────
    initial_state: AgentState = {
        "sim_data":            sim_data,
        "traffic_status":      "",
        "proposed_route":      [],
        "explanation":         "",
        "is_safe":             True,
        "rejection_reason":    None,
        "final_communication": "",
    }

    # ── Run the agent pipeline ────────────────────────────────────
    app = build_graph()
    final_state = app.invoke(initial_state)

    # ── Output results ────────────────────────────────────────────
    if args.output == "json":
        result = {
            "source":               sim_data.source,
            "destination":          sim_data.destination,
            "checked_edge":         sim_data.checked_edge,
            "vehicles":             sim_data.vehicles,
            "density":              sim_data.density,
            "timestamp":            sim_data.timestamp,
            "traffic_status":       final_state["traffic_status"],
            "proposed_route":       final_state["proposed_route"],
            "explanation":          final_state["explanation"],
            "is_safe":              final_state["is_safe"],
            "rejection_reason":     final_state["rejection_reason"],
            "final_communication":  final_state["final_communication"],
        }
        print(json.dumps(result, indent=2))

    else:
        # Pretty print (same as graph.py but with CLI context)
        print("=" * 55)
        print("   🚦 TRAFFIC ROUTING & SAFETY AGENT PIPELINE")
        print("=" * 55)
        print(f"  Source → Destination : {sim_data.source} → {sim_data.destination}")
        print(f"  Current Edge         : {sim_data.checked_edge}")
        print(f"  Vehicles on Network  : {sim_data.vehicles}")
        print(f"  Road Density         : {sim_data.density:.4f}")
        print(f"  Timestamp            : {sim_data.timestamp}s")
        print("-" * 55)
        print(f"  [Agent 1] Traffic    : {final_state['traffic_status']}")
        print(f"  [Agent 2] Route      : {final_state['proposed_route']}")
        print(f"  [Agent 2] Reason     : {final_state['explanation']}")
        print(f"  [Agent 3] Safe?      : {'✅ Yes' if final_state['is_safe'] else '🚨 No'}")
        if not final_state["is_safe"]:
            print(f"  [Agent 3] Warning    : {final_state['rejection_reason']}")
        print("-" * 55)
        if final_state.get("final_communication"):
            print(f"\n  🚗 DRIVER MESSAGE: {final_state['final_communication']}")
        else:
            print(f"\n  🚨 PIPELINE HALTED: Route rejected by Safety Agent.")
        print("=" * 55)


if __name__ == "__main__":
    main()