# graph.py
from langgraph.graph import StateGraph, END
from state import AgentState
from nodes import traffic_agent_node, routing_agent_node, safety_agent_node, communication_agent_node

workflow = StateGraph(AgentState)

# 1. Add all 4 agent nodes
workflow.add_node("traffic_agent", traffic_agent_node)
workflow.add_node("routing_agent", routing_agent_node)
workflow.add_node("safety_agent", safety_agent_node)
workflow.add_node("communication_agent", communication_agent_node) # NEW

# 2. Define the flow
workflow.set_entry_point("traffic_agent")
workflow.add_edge("traffic_agent", "routing_agent")
workflow.add_edge("routing_agent", "safety_agent")

# 3. The Conditional Loop
def check_safety_verdict(state: AgentState):
    if state["is_safe"]:
        return "approved"
    return "rejected"

workflow.add_conditional_edges(
    "safety_agent",
    check_safety_verdict,
    {
        "approved": "communication_agent",  # NEW: Hand off to Communication Agent if safe
        "rejected": "routing_agent"  
    }
)

# 4. Final step
workflow.add_edge("communication_agent", END) # NEW: End the graph after communication

app = workflow.compile()