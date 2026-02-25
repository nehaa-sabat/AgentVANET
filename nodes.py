import os
import json
import openai
from dotenv import load_dotenv
from state import AgentState

load_dotenv()

# --- Agent 1: Traffic Agent (Rule-Based Analyst) ---
def traffic_agent_node(state: AgentState):
    data = state["sim_data"]
    
    # The new JSON already calculates the congestion level, so we just extract it.
    status = f"{data.congestion_level} Congestion"
        
    return {"traffic_status": status}

# --- Agent 2: Routing Agent (LLM Reasoner) ---
def routing_agent_node(state: AgentState):
    client = openai.OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=os.environ.get("GROQ_API_KEY")
    ) 
    
    data = state['sim_data']
    
    prompt = f"""
    You are an intelligent routing agent for a vehicular network.
    Current edge with congestion: {data.checked_edge}
    Traffic status: {state['traffic_status']}
    Available detour route: {', '.join(data.selected_route)}
    Destination: {data.destination}
    Previous rejection reason (if any): {state.get('rejection_reason', 'None')}
    
    Based on this, suggest a route ('stay on current edge' or 'take detour route') and explain why briefly.
    You MUST output a valid JSON object with exactly two keys: "proposed_route" and "explanation".
    """
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    # Safely extracting the first item from the list using index 0
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
    
    # Rule: If physical density is dangerously high (> 0.8), reject the route.
    if data.density > 0.8:
        return {
            "is_safe": False, 
            "rejection_reason": f"Road density is {data.density}, which exceeds physical safety limits."
        }
        
    return {"is_safe": True, "rejection_reason": ""}

# --- Agent 4: Communication Agent (Dashboard Interface) ---
def communication_agent_node(state: AgentState):
    client = openai.OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=os.environ.get("GROQ_API_KEY")
    ) 
    
    data = state['sim_data']
    
    # Prompt the LLM to act as a driver-facing dashboard assistant
    prompt = f"""
    You are the Communication Agent for a vehicle's smart dashboard.
    Your job is to write a short, friendly alert for the driver based on the system's technical routing decision.
    
    Original destination: {data.destination}
    New Route Approved: {state['proposed_route']}
    Technical Reason: {state['explanation']}
    
    Write a brief, 1-to-2 sentence notification telling the driver about the route change and why it is happening.
    You MUST output a valid JSON object with exactly one key: "driver_message".
    """
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    output_text = response.choices[0].message.content    
    
    try:
        ai_message = json.loads(output_text)
        driver_msg = ai_message.get("driver_message", "Route updated for safety and efficiency.")
    except json.JSONDecodeError:
        driver_msg = "Route updated for safety and efficiency."
        
    return {"final_communication": driver_msg}