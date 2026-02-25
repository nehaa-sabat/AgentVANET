# main.py
import json
from state import NewTrafficData
from graph import app

def run_agent_system(file_path: str):
    print(f"\n{'='*50}")
    print(f"Executing 4-Agent System for: {file_path}")
    print(f"{'='*50}")
    
    with open(file_path, "r") as f:
        data_dict = json.load(f)

    validated_data = NewTrafficData(**data_dict)

    # Initialize memory with the new field included
    initial_state = {
        "sim_data": validated_data,
        "traffic_status": "",
        "proposed_route": "",
        "explanation": "",
        "is_safe": False,
        "rejection_reason": "",
        "final_communication": "" # NEW
    }

    print("Agents are collaborating...\n")
    final_state = app.invoke(initial_state)

    # Print the background technical workflow
    print(f"[1] Traffic Agent:   {final_state['traffic_status']}")
    print(f"[2] Routing Agent:   Chose '{final_state['proposed_route']}'")
    print(f"    Explanation:     {final_state['explanation']}") # THIS LINE WAS MISSING
    print(f"[3] Safety Agent:    {'✅ APPROVED' if final_state['is_safe'] else '❌ REJECTED'}")
    
    # Print the user-facing output
    if final_state['is_safe']:
        print(f"[4] Communication Agent (Output to Dashboard):")
        print(f"    📢 \"{final_state['final_communication']}\"")

if __name__ == "__main__":
    run_agent_system("decision_output.json")