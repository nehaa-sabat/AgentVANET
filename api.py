from fastapi import FastAPI
from state import NewTrafficData
from graph import app as agent_workflow

# Initialize the FastAPI application
api = FastAPI(title="AgentVANET API", description="Multi-Agent AI Routing System")

# Create a POST endpoint that the React dashboard will call
@api.post("/process_traffic")
async def process_traffic(data: NewTrafficData):
    """
    Receives traffic data from the dashboard/simulator, runs the multi-agent 
    workflow, and returns the AI's final decisions.
    """
    # 1. Initialize the LangGraph memory clipboard with the incoming API data
    initial_state = {
        "sim_data": data,
        "traffic_status": "",
        "proposed_route": "",
        "explanation": "",
        "is_safe": False,
        "rejection_reason": "",
        "final_communication": "" 
    }

    # 2. Run the 4-agent workflow
    final_state = agent_workflow.invoke(initial_state)

    # 3. Format and return the results as a clean JSON response for the dashboard
    return {
        "traffic_status": final_state["traffic_status"],
        "proposed_route": final_state["proposed_route"],
        "explanation": final_state["explanation"],
        "is_safe": final_state["is_safe"],
        "dashboard_message": final_state["final_communication"]
    }