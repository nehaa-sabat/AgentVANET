from pydantic import BaseModel
from typing import TypedDict

# 1. The strict data contract for the SUMO JSON (from your working code)
class SimulationStep(BaseModel):
    step: int
    total_vehicle_count: int
    avg_speed_network: float
    edge: str
    edge_vehicle_count: int
    edge_density: float
    edge_travel_time: float

# 2. We add a new Pydantic model specifically to force the AI to output clean data
class RouteProposal(BaseModel):
    proposed_route: str
    explanation: str

# 3. The shared clipboard that tracks the agents' decisions
class AgentState(TypedDict):
    sim_data: SimulationStep  
    traffic_status: str       
    proposed_route: str       
    explanation: str          
    is_safe: bool             
    rejection_reason: str