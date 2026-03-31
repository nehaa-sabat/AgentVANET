import json
import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
import uvicorn

from graph import build_graph, load_sim_data
from nodes import run_all_models
from state import AgentState

# ──────────────────────────────────────────────
# App Setup
# ──────────────────────────────────────────────
app = FastAPI(title="Traffic Routing & Safety Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# ──────────────────────────────────────────────
# Response Schemas
# ──────────────────────────────────────────────
class PipelineResponse(BaseModel):
    source: str
    destination: str
    checked_edge: str
    vehicles: int
    density: float
    congestion_level: str
    selected_route: List[str]
    alternate_route: List[str]
    timestamp: int
    traffic_status: str
    proposed_route: List[str]
    explanation: str
    is_safe: bool
    rejection_reason: Optional[str]
    final_communication: str
    routing_time_s: float = 0.0
    comm_time_s: float = 0.0
    total_time_s: float = 0.0
    estimated_delay_min: float = 0.0


class ModelResult(BaseModel):
    model_name: str
    traffic_status: str
    proposed_route: List[str]
    explanation: str
    is_safe: bool
    rejection_reason: Optional[str]
    final_communication: str
    routing_time_s: float = 0.0
    comm_time_s: float = 0.0
    total_time_s: float = 0.0
    estimated_delay_min: float = 0.0


class CompareResponse(BaseModel):
    source: str
    destination: str
    checked_edge: str
    vehicles: int
    density: float
    congestion_level: str
    selected_route: List[str]
    alternate_route: List[str]
    timestamp: int
    models: dict  # keyed by "llama" and "gemma"


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
def _run_pipeline(sim_data) -> dict:
    initial_state: AgentState = {
        "sim_data":            sim_data,
        "traffic_status":      "",
        "proposed_route":      [],
        "explanation":         "",
        "is_safe":             True,
        "rejection_reason":    None,
        "final_communication": "",
        "routing_time_s":      0.0,
        "comm_time_s":         0.0,
        "total_time_s":        0.0,
        "estimated_delay_min": 0.0,
    }
    return build_graph().invoke(initial_state)


def _normalize_route(route) -> List[str]:
    if isinstance(route, list):
        return [str(r) for r in route]
    if isinstance(route, str):
        return [r.strip() for r in route.replace("->", ",").split(",") if r.strip()]
    return [str(route)]


def _load(source: str, destination: str):
    """Shared helper to load sim_data for a source/destination pair."""
    try:
        return load_sim_data(path="dataset.json", source=source, destination=destination)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (IndexError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))


# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────

@app.get("/", tags=["Frontend"])
def serve_frontend():
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return {"status": "API running", "docs": "/docs"}


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}


@app.get("/network", tags=["Network"])
def get_network():
    """Returns full road network topology + vehicle positions for the map."""
    try:
        with open("dataset.json", "r") as f:
            raw_data = json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="dataset.json not found.")

    latest_step = raw_data["steps"][-1]

    edges = [
        {
            "id":            e["id"],
            "source":        e["id"].split("_")[0],
            "target":        e["id"].split("_")[1],
            "vehicle_count": e["vehicle_count"],
            "mean_speed":    round(e["mean_speed"], 2),
            "occupancy":     round(e["occupancy"], 4),
            "waiting_time":  e["waiting_time"],
            "congestion": (
                "HIGH"   if e["mean_speed"] < 5.0  else
                "MEDIUM" if e["mean_speed"] < 12.0 else
                "LOW"
            ),
        }
        for e in latest_step["edges"]
        if not e["id"].startswith(":")
    ]

    nodes = sorted(set(n for e in edges for n in [e["source"], e["target"]]))

    vehicles = [
        {
            "id":    v["id"],
            "road":  v["road"],
            "route": v["route"],
            "speed": round(v["speed"], 2),
            "type":  v.get("type", "car"),
        }
        for v in latest_step["vehicles"]
    ]

    return {"nodes": nodes, "edges": edges, "vehicles": vehicles, "time": latest_step["time"]}


@app.get("/analyze", response_model=PipelineResponse, tags=["Pipeline"])
def analyze(
    source: str = Query(..., description="Source node, e.g. A"),
    destination: str = Query(..., description="Destination node, e.g. D"),
):
    """Run the full 4-agent pipeline (single model) for a source to destination pair."""
    if source == destination:
        raise HTTPException(status_code=400, detail="Source and destination must be different.")

    sim_data    = _load(source, destination)
    final_state = _run_pipeline(sim_data)

    return PipelineResponse(
        source=sim_data.source,
        destination=sim_data.destination,
        checked_edge=sim_data.checked_edge,
        vehicles=sim_data.vehicles,
        density=sim_data.density,
        congestion_level=sim_data.congestion_level,
        selected_route=sim_data.selected_route,
        alternate_route=sim_data.alternate_route,
        timestamp=sim_data.timestamp,
        traffic_status=final_state["traffic_status"],
        proposed_route=_normalize_route(final_state["proposed_route"]),
        explanation=final_state["explanation"],
        is_safe=final_state["is_safe"],
        rejection_reason=final_state["rejection_reason"],
        final_communication=final_state.get("final_communication", ""),
        routing_time_s=final_state.get("routing_time_s", 0.0),
        comm_time_s=final_state.get("comm_time_s", 0.0),
        total_time_s=final_state.get("total_time_s", 0.0),
        estimated_delay_min=final_state.get("estimated_delay_min", 0.0),
    )


@app.get("/compare", response_model=CompareResponse, tags=["Compare"])
def compare(
    source: str = Query(..., description="Source node, e.g. A"),
    destination: str = Query(..., description="Destination node, e.g. D"),
):
    """Run LLaMA 3.3 70B and Gemma2 9B in parallel and return both outputs for comparison."""
    if source == destination:
        raise HTTPException(status_code=400, detail="Source and destination must be different.")

    sim_data     = _load(source, destination)
    model_results = run_all_models(sim_data)

    # Normalize proposed_route for each model
    for key in model_results:
        model_results[key]["proposed_route"] = _normalize_route(
            model_results[key]["proposed_route"]
        )

    return CompareResponse(
        source=sim_data.source,
        destination=sim_data.destination,
        checked_edge=sim_data.checked_edge,
        vehicles=sim_data.vehicles,
        density=sim_data.density,
        congestion_level=sim_data.congestion_level,
        selected_route=sim_data.selected_route,
        alternate_route=sim_data.alternate_route,
        timestamp=sim_data.timestamp,
        models=model_results,
    )


@app.get("/nodes", tags=["Network"])
def get_available_nodes():
    """Returns all nodes available in the road network."""
    try:
        with open("dataset.json", "r") as f:
            raw_data = json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="dataset.json not found.")

    latest_step = raw_data["steps"][-1]
    edges = [e for e in latest_step["edges"] if not e["id"].startswith(":")]
    nodes = sorted(set(n for e in edges for n in e["id"].split("_")))
    return {"nodes": nodes}


# ──────────────────────────────────────────────
# Run
# ──────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)