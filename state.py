from pydantic import BaseModel
from typing import List, TypedDict

# 1. The Pydantic model for the new dataset
class NewTrafficData(BaseModel):
    source: str
    destination: str
    checked_edge: str
    vehicles: int
    density: float
    congestion_level: str
    selected_route: List[str]
    timestamp: int

# 2. The shared clipboard for the agents
class AgentState(TypedDict):
    sim_data: NewTrafficData
    traffic_status: str
    proposed_route: str
    explanation: str
    is_safe: bool
    rejection_reason: str
    final_communication: str