import os
import json
import openai
from dotenv import load_dotenv
from state import AgentState

load_dotenv()

MODELS = {
    "llama": "llama-3.3-70b-versatile",
    "gemma": "llama-3.1-8b-instant",
}

MODEL_LABELS = {
    "llama": "LLaMA 3.3 70B",
    "gemma": "LLaMA 3.1 8B",
}


def get_client():
    return openai.OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=os.environ.get("GROQ_API_KEY")
    )


def fmt_path(path):
    if not path:
        return "N/A"
    nodes = []
    for edge in path:
        parts = edge.split("_")
        if len(parts) == 2:
            if not nodes:
                nodes.append(parts[0])
            nodes.append(parts[1])
    return " -> ".join(nodes) + f"  (edges: {', '.join(path)})"


def build_routing_prompt(data, traffic_status):
    all_paths_str = "\n".join(
        f"  Path {i+1}: {fmt_path(p)}"
        for i, p in enumerate(data.all_paths[:5])
    ) if data.all_paths else "  Only one path available."

    return f"""
You are an intelligent routing agent for a vehicular ad-hoc network (VANET).

Trip Request:
  Source      : {data.source}
  Destination : {data.destination}

Network Analysis:
  Most congested edge on best path : {data.checked_edge}
  Traffic status on that edge      : {traffic_status}
  Road density                     : {data.density:.4f}

Available Paths (ranked best to worst congestion):
{all_paths_str}

Best Path     : {fmt_path(data.selected_route)}
Alternate Path: {fmt_path(data.alternate_route)}

DECISION RULES:
1. If traffic status is LOW Congestion or MEDIUM Congestion: Choose "best".
2. If traffic status is HIGH Congestion: Choose "alternate" if it exists, else "best".

IMPORTANT: Output a valid JSON object with exactly two keys:
  "choice": either the string "best" or the string "alternate"
  "explanation": one sentence explaining your decision

Do NOT output edge IDs. Just output "best" or "alternate" for the choice.
"""


def build_comm_prompt(data, proposed, explanation, is_safe, rejection_reason):
    if isinstance(proposed, list) and proposed:
        nodes = []
        for edge in proposed:
            parts = edge.split("_")
            if len(parts) == 2:
                if not nodes:
                    nodes.append(parts[0])
                nodes.append(parts[1])
        route_readable = " -> ".join(nodes)
    else:
        route_readable = str(proposed)

    safety_str = "SAFE" if is_safe else f"UNSAFE - {rejection_reason}"

    return f"""
You are the Communication Agent for a vehicle smart dashboard.
Write a short friendly 1-sentence alert for the driver.

Trip: {data.source} to {data.destination}
Chosen Route: {route_readable}
Technical Reason: {explanation}
Safety Status: {safety_str}
Congestion Level: {data.congestion_level}

INSTRUCTIONS:
- If SAFE and LOW/MEDIUM congestion: tell driver route is clear.
- If SAFE and took alternate route: mention the reroute.
- If UNSAFE: warn driver calmly.
- Include the route like A to B to C in the message.
- Keep it to exactly 1 sentence.

Output a valid JSON object with exactly one key: "driver_message".
"""


def call_llm(client, model_name, prompt):
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            timeout=30,
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"[{model_name}] Error: {e}")
        return None


# ──────────────────────────────────────────────
# Agent 1: Traffic Agent (Rule-Based)
# ──────────────────────────────────────────────
def traffic_agent_node(state: AgentState):
    data = state["sim_data"]
    return {"traffic_status": f"{data.congestion_level} Congestion"}


# ──────────────────────────────────────────────
# Agent 2: Routing Agent (default: llama)
# ──────────────────────────────────────────────
def routing_agent_node(state: AgentState):
    return routing_agent_node_for_model(state, model_key="llama")


def routing_agent_node_for_model(state: AgentState, model_key: str = "llama"):
    import time
    client     = get_client()
    data       = state["sim_data"]
    model_name = MODELS.get(model_key, MODELS["llama"])
    prompt     = build_routing_prompt(data, state["traffic_status"])

    t_start = time.time()
    result  = call_llm(client, model_name, prompt)
    routing_time = round(time.time() - t_start, 2)

    if result:
        choice      = result.get("choice", "best").strip().lower()
        explanation = result.get("explanation", "No explanation provided.")
        if choice == "alternate" and data.alternate_route:
            route = data.alternate_route
        else:
            route = data.selected_route
    else:
        route       = data.selected_route
        explanation = f"{model_name} failed to respond; defaulting to best path."

    # Estimated delay based on route length and congestion
    congestion_penalty = {"HIGH": 8, "MEDIUM": 4, "LOW": 1}
    estimated_delay = round(len(route) * 2 * congestion_penalty.get(data.congestion_level, 1), 1)

    return {
        "proposed_route":      route,
        "explanation":         explanation,
        "routing_time_s":      routing_time,
        "estimated_delay_min": estimated_delay,
    }


# ──────────────────────────────────────────────
# Agent 3: Safety Agent (Rule-Based)
# ──────────────────────────────────────────────
def safety_agent_node(state: AgentState):
    data = state["sim_data"]
    if data.density > 0.8:
        return {
            "is_safe": False,
            "rejection_reason": (
                f"Road density {data.density:.2f} on {data.checked_edge} "
                f"exceeds the 0.8 physical safety limit."
            )
        }
    if data.congestion_level == "HIGH":
        return {
            "is_safe": False,
            "rejection_reason": (
                f"HIGH congestion detected on {data.checked_edge}. "
                f"Route flagged for safety review."
            )
        }
    return {"is_safe": True, "rejection_reason": None}


# ──────────────────────────────────────────────
# Agent 4: Communication Agent (default: llama)
# ──────────────────────────────────────────────
def communication_agent_node(state: AgentState):
    return communication_agent_node_for_model(state, model_key="llama")


def communication_agent_node_for_model(state: AgentState, model_key: str = "llama"):
    import time
    client     = get_client()
    data       = state["sim_data"]
    model_name = MODELS.get(model_key, MODELS["llama"])
    prompt     = build_comm_prompt(
        data, state["proposed_route"], state["explanation"],
        state["is_safe"], state["rejection_reason"],
    )
    t_start  = time.time()
    result   = call_llm(client, model_name, prompt)
    comm_time = round(time.time() - t_start, 2)

    driver_msg = result.get("driver_message", "Route confirmed.") if result else "Route confirmed."

    total_time = round(
        state.get("routing_time_s", 0) + comm_time, 2
    )

    return {
        "final_communication": driver_msg,
        "comm_time_s":         comm_time,
        "total_time_s":        total_time,
    }


# ──────────────────────────────────────────────
# Multi-model runner (used by /compare endpoint)
# ──────────────────────────────────────────────
def run_all_models(sim_data) -> dict:
    """Run routing + communication for both models independently.
    Traffic and Safety agents are rule-based so they run once."""
    import time

    traffic_status = f"{sim_data.congestion_level} Congestion"

    # Safety check (same for both models)
    if sim_data.density > 0.8:
        is_safe          = False
        rejection_reason = (
            f"Road density {sim_data.density:.2f} on {sim_data.checked_edge} "
            f"exceeds the 0.8 physical safety limit."
        )
    elif sim_data.congestion_level == "HIGH":
        is_safe          = False
        rejection_reason = (
            f"HIGH congestion detected on {sim_data.checked_edge}. "
            f"Route flagged for safety review."
        )
    else:
        is_safe          = True
        rejection_reason = None

    client  = get_client()
    results = {}

    for model_key, model_name in MODELS.items():
        t_start = time.time()

        # Routing — LLM only decides "best" or "alternate", we use actual BFS edges
        routing_result = call_llm(
            client, model_name,
            build_routing_prompt(sim_data, traffic_status)
        )
        t_routing = time.time()

        if routing_result:
            choice      = routing_result.get("choice", "best").strip().lower()
            explanation = routing_result.get("explanation", "No explanation.")
            route = sim_data.alternate_route if (choice == "alternate" and sim_data.alternate_route) else sim_data.selected_route
        else:
            route       = sim_data.selected_route
            explanation = f"{model_name} failed to respond."

        # Communication
        comm_result = call_llm(
            client, model_name,
            build_comm_prompt(sim_data, route, explanation, is_safe, rejection_reason)
        )
        t_end = time.time()

        driver_msg = (
            comm_result.get("driver_message", "Route confirmed.")
            if comm_result else "Route confirmed."
        )

        routing_time = round(t_routing - t_start, 2)
        comm_time    = round(t_end - t_routing, 2)
        total_time   = round(t_end - t_start, 2)

        # Estimated delay: based on congestion level and route length
        congestion_penalty = {"HIGH": 8, "MEDIUM": 4, "LOW": 1}
        base_delay = len(route) * 2  # 2 min per hop base
        delay_multiplier = congestion_penalty.get(sim_data.congestion_level, 1)
        estimated_delay = round(base_delay * delay_multiplier, 1)

        results[model_key] = {
            "model_name":          model_name,
            "traffic_status":      traffic_status,
            "proposed_route":      route,
            "explanation":         explanation,
            "is_safe":             is_safe,
            "rejection_reason":    rejection_reason,
            "final_communication": driver_msg,
            "routing_time_s":      routing_time,
            "comm_time_s":         comm_time,
            "total_time_s":        total_time,
            "estimated_delay_min": estimated_delay,
        }

    return results