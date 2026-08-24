import osmnx as ox
import networkx as nx

place_name = "San Francisco, California, USA"
G = ox.graph_from_place(place_name, network_type='drive')

print(f"Graph loaded: {len(G.nodes)} nodes, {len(G.edges)} edges")

G = ox.add_edge_speeds(G)
G = ox.add_edge_travel_times(G)

ox.save_graphml(G, "data/city_graph.graphml")
print("Graph saved to data/city_graph.graphml")