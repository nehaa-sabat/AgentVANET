from langgraph.graph import StateGraph, END
from state import AgentState
from nodes import traffic_agent_node, routing_agent_node, safety_agent_node

# 1. Initialize the graph
workflow = StateGraph(AgentState)

# 2. Add the agent nodes
workflow.add_node("traffic_agent", traffic_agent_node)
workflow.add_node("routing_agent", routing_agent_node)
workflow.add_node("safety_agent", safety_agent_node)

# 3. Define the standard flow
workflow.set_entry_point("traffic_agent")
workflow.add_edge("traffic_agent", "routing_agent")
workflow.add_edge("routing_agent", "safety_agent")

# 4. Define the routing logic for the Safety loop
def check_safety_verdict(state: AgentState):
    if state["is_safe"] == True:
        return "approved"
    else:
        return "rejected"

workflow.add_conditional_edges(
    "safety_agent",
    check_safety_verdict,
    {
        "approved": END,             # Finish if safe
        "rejected": "routing_agent"  # Loop back to AI if unsafe
    }
)

# 5. Compile the application
app = workflow.compile()