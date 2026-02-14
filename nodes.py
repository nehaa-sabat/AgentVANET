import os
import json
from urllib import response
import openai
from dotenv import load_dotenv
from state import AgentState, RouteProposal

load_dotenv()

# --- Agent 1: Traffic Agent (Rule-Based Analyst) ---
def traffic_agent_node(state: AgentState):
    data = state["sim_data"]
    
    if data.avg_speed_network < 5.0 and data.edge_density > 0.5:
        status = "High Congestion"
    elif data.avg_speed_network < 8.0:
        status = "Medium Traffic"
    else:
        status = "Low Traffic - Free Flowing"
        
    return {"traffic_status": status}

# --- Agent 2: Routing Agent (LLM Reasoner) ---
# --- Agent 2: Routing Agent (LLM Reasoner) ---
def routing_agent_node(state: AgentState):
    import os
    import json
    import openai
    
    # 1. Point the client to Groq
    client = openai.OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=os.environ.get("GROQ_API_KEY")
    ) 
    
    # 2. Explicitly instruct the model to return JSON in the prompt
    prompt = f"""
    You are an intelligent routing agent for a vehicular network.
    Current edge: {state['sim_data'].edge}
    Traffic status: {state['traffic_status']}
    Previous rejection reason (if any): {state.get('rejection_reason', 'None')}
    
    Based on this, suggest a route ('stay on current edge' or 'detour to new edge') and explain why briefly.
    You MUST output a valid JSON object with exactly two keys: "proposed_route" and "explanation".
    """
    
    # 3. Use standard.create() and {"type": "json_object"}
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    # 4. Safely parse the JSON string returned by Groq (Notice the  right after choices)
    output_text = response.choices[0].message.content    
    try:
        ai_decision = json.loads(output_text)
        route = ai_decision.get("proposed_route", "Unknown")
        explanation = ai_decision.get("explanation", output_text)
    except json.JSONDecodeError:
        route = "Unknown"
        explanation = "Failed to parse JSON"
        
    return {
        "proposed_route": route, 
        "explanation": explanation
    }
    
# --- Agent 3: Safety Agent (Rule-Based Validator) ---
def safety_agent_node(state: AgentState):
    data = state["sim_data"]
    proposed = state["proposed_route"]
    
    if "current" in proposed.lower() and data.edge_travel_time > 300.0:
        return {"is_safe": False, "rejection_reason": "Travel time indicates severe gridlock."}
        
    return {"is_safe": True, "rejection_reason": ""}