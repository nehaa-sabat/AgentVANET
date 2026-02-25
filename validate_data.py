import json
from pydantic import BaseModel
from typing import List

# 1. Define the strict data contract for the NEW JSON format
# Notice how these exactly match your new keys, including the list for the route
class NewTrafficData(BaseModel):
    source: str
    destination: str
    checked_edge: str
    vehicles: int
    density: float
    congestion_level: str
    selected_route: List[str]
    timestamp: int

# 2. Create a function to read and validate the new JSON
def validate_traffic_data(file_path: str) -> NewTrafficData:
    with open(file_path, 'r') as file:
        data_dict = json.load(file)
        
    # Validate the dictionary using our new Pydantic class
    validated_data = NewTrafficData(**data_dict)
    
    return validated_data

# --- Testing the Validation ---
if __name__ == "__main__":
    # Replace with the actual name of your new JSON file if it is different
    file_name = "decision_output.json" 
    
    print(f"--- Testing {file_name} ---")
    try:
        current_data = validate_traffic_data(file_name)
        
        print("✅ Validation Successful! The data is clean.")
        print(f"Routing from {current_data.source} to {current_data.destination}")
        print(f"Checking Edge: {current_data.checked_edge}")
        print(f"Congestion Level: {current_data.congestion_level}")
        print(f"Proposed Route Array: {current_data.selected_route}")
        
    except Exception as e:
        print(f"❌ Validation Failed: {e}")