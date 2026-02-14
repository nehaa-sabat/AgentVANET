import json
from pydantic import BaseModel

# 1. Define the strict data contract using Pydantic
# Notice how the variable names exactly match the keys in your JSON image
class SimulationStep(BaseModel):
    step: int
    total_vehicle_count: int
    avg_speed_network: float
    edge: str
    edge_vehicle_count: int
    edge_density: float
    edge_travel_time: float

# 2. Create a function to read the JSON and apply the Pydantic model
def get_latest_traffic_state(file_path: str) -> SimulationStep:
    # Open and read the raw JSON file
    with open(file_path, 'r') as file:
        raw_data = json.load(file)
    
    # Your JSON is a list of steps. We want the most recent one (the last item).
    latest_step_data = raw_data[-1]
    
    # 3. Validate the data by passing it into the Pydantic class
    # The '**' unpacks the dictionary so Pydantic can check every single field
    validated_state = SimulationStep(**latest_step_data)
    
    return validated_state


# --- Testing the code ---
if __name__ == "__main__":
    # 1. Put all your exact file names into a list
    datasets = [
        "low_traffic1.json", 
        "medium_traffic1.json", 
        "high_traffic1.json"
    ]
    
    # 2. Create a loop to go through each file in the list one by one
    for current_file in datasets:
        print(f"\n--- Analyzing file: {current_file} ---")
        
        # 3. Pass the 'current_file' variable into your function instead of a hardcoded string
        current_state = get_latest_traffic_state(current_file)
        
        # 4. Print the safely extracted data
        print(f"Current Step: {current_state.step}")
        print(f"Average Speed: {current_state.avg_speed_network}")


