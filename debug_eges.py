import json
from collections import deque

with open("dataset.json", "r") as f:
    raw_data = json.load(f)

latest_step = raw_data["steps"][-1]
all_edges   = latest_step["edges"]

# Build network
graph = {}
edge_map = {}
for e in all_edges:
    eid = e["id"]
    if eid.startswith(":"):
        continue
    parts = eid.split("_")
    if len(parts) != 2:
        continue
    src, tgt = parts
    graph.setdefault(src, [])
    graph.setdefault(tgt, [])
    graph[src].append((tgt, eid, e.get("mean_speed", 20.0)))
    edge_map[eid] = e

print("=== NETWORK GRAPH ===")
for node, neighbors in graph.items():
    for n, eid, spd in neighbors:
        print(f"  {node} -> {n}  via {eid}  speed={spd:.2f}")

print("\n=== BFS ALL PATHS A -> D ===")
queue = deque()
queue.append(("A", [], {"A"}))
all_paths = []

while queue:
    current, edge_path, visited = queue.popleft()
    if len(edge_path) > 8:
        continue
    if current == "D":
        if edge_path:
            all_paths.append(edge_path)
        continue
    for neighbor, edge_id, speed in graph.get(current, []):
        if neighbor not in visited:
            queue.append((neighbor, edge_path + [edge_id], visited | {neighbor}))

for i, p in enumerate(all_paths):
    print(f"  Path {i+1}: {p}")

print("\n=== ENSURE COMPLETE PATH TEST ===")
for path in all_paths:
    nodes = []
    for edge in path:
        parts = edge.split("_")
        if len(parts) == 2:
            if not nodes:
                nodes.append(parts[0])
            nodes.append(parts[1])
    print(f"  Nodes from path {path}: {nodes}")

    complete = []
    for i in range(len(nodes) - 1):
        src_n, tgt_n = nodes[i], nodes[i+1]
        fwd = f"{src_n}_{tgt_n}"
        rev = f"{tgt_n}_{src_n}"
        if fwd in edge_map:
            complete.append(fwd)
        elif rev in edge_map:
            complete.append(rev)
        else:
            complete.append(f"MISSING:{fwd}")
    print(f"  Complete edges: {complete}")
    print()