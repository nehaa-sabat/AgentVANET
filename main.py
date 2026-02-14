import json
from state import SimulationStep
from graph import app

# Your exact working function
def get_latest_traffic_state(file_path: str) -> SimulationStep:
    with open(file_path, 'r') as file:
        raw_data = json.load(file)
    latest_step_data = raw_data[-1]
    return SimulationStep(**latest_step_data)

if __name__ == "__main__":
    # Add all your JSON files here
    datasets = [
        "low_traffic1.json", 
        "medium_traffic1.json", 
        "high_traffic1.json"
    ]
    
    for file_path in datasets:
        print(f"\n{'='*40}")
        print(f"Executing Agents for: {file_path}")
        print(f"{'='*40}")
        
        # 1. Load and validate data
        current_state = get_latest_traffic_state(file_path)
        
        # 2. Initialize the graph's memory
        initial_state = {
            "sim_data": current_state,
            "traffic_status": "",
            "proposed_route": "",
            "explanation": "",
            "is_safe": False,
            "rejection_reason": ""
        }
        
        # 3. Run the workflow
        final_state = app.invoke(initial_state)
        
        # 4. Output the results
        print(f"Traffic Agent Diagnosis: {final_state['traffic_status']}")
        print(f"Routing Agent Decision:  {final_state['proposed_route']}")
        print(f"Routing Agent Reasoning: {final_state['explanation']}")
        print(f"Safety Agent Verdict:    {'APPROVED' if final_state['is_safe'] else 'REJECTED'}")