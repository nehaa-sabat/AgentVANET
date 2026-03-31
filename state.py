from pydantic import BaseModel, Field
from typing import List, Optional, TypedDict

class NewTrafficData(BaseModel):
    source: str
    destination: str
    checked_edge: str
    vehicles: int
    density: float
    congestion_level: str
    selected_route: List[str]           # Best (lowest congestion) path
    alternate_route: List[str] = Field(default_factory=list)  # Second-best path
    all_paths: List[List[str]] = Field(default_factory=list)  # All BFS paths found
    timestamp: int

class AgentState(TypedDict):
    sim_data: NewTrafficData
    traffic_status: str
    proposed_route: List[str]
    explanation: str
    is_safe: bool
    rejection_reason: Optional[str]
    final_communication: str
    routing_time_s: float
    comm_time_s: float
    total_time_s: float
    estimated_delay_min: float