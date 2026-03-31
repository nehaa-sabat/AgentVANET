import json
from pydantic import BaseModel
from typing import List

class NewTrafficData(BaseModel):
    source: str
    destination: str
    checked_edge: str
    vehicles: int
    density: float
    congestion_level: str
    selected_route: List[str]
    timestamp: int

def extract_and_validate():
    print("Starting dataset validation...")
    try:
        with open("dataset.json", "r") as file:
            raw_data = json.load(file)
            
        latest_step = raw_data["steps"][-1]
        
        # vehicles is a list — grab the FIRST vehicle
        target_vehicle = latest_step["vehicles"][0]
        
        full_route   = target_vehicle["route"]  # e.g. ["A_E", "E_F", "F_D"]
        current_road = target_vehicle["road"]   # e.g. "F_D"
        
        # full_route is a list of strings, split the first and last edges
        source_node = full_route[0].split("_")[0]   # "A_E" -> "A"
        dest_node   = full_route[-1].split("_")[1]  # "F_D" -> "D"
        
        edge_info = next((e for e in latest_step["edges"] if e["id"] == current_road), None)
        
        density        = edge_info["occupancy"]  if edge_info else 0.0
        mean_speed     = edge_info["mean_speed"] if edge_info else 20.0
        total_vehicles = len(latest_step["vehicles"])
        
        if mean_speed < 5.0:
            congestion = "HIGH"
        elif mean_speed < 12.0:
            congestion = "MEDIUM"
        else:
            congestion = "LOW"
            
        mapped_data = {
            "source":          source_node,
            "destination":     dest_node,
            "checked_edge":    current_road,
            "vehicles":        total_vehicles,
            "density":         density,
            "congestion_level": congestion,
            "selected_route":  full_route,   # already a List[str]
            "timestamp":       int(latest_step["time"]),
        }  # <-- this closing brace was missing

        validated_data = NewTrafficData(**mapped_data)
        
        print("\n✅ SUCCESS: Raw SUMO data extracted and validated perfectly!")
        print("-" * 50)
        print(f"Source Node:      {validated_data.source}")
        print(f"Destination Node: {validated_data.destination}")
        print(f"Vehicle on Edge:  {validated_data.checked_edge}")
        print(f"Road Density:     {validated_data.density}")
        print(f"AI Congestion:    {validated_data.congestion_level} (Speed: {mean_speed} m/s)")
        print(f"Proposed Route:   {validated_data.selected_route}")
        print("-" * 50)
        
    except Exception as e:
        print(f"\n❌ ERROR: Something went wrong during extraction.")
        import traceback; traceback.print_exc()

if __name__ == "__main__":
    extract_and_validate()