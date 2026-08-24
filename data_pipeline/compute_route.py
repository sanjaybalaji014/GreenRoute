import osmnx as ox
import networkx as nx
import numpy as np
import time as time_module
from traffic import get_congestion_factor
from vehicle_data import compute_fuel_cost_and_emissions

G = ox.load_graphml("data/city_graph.graphml")
print(f"Graph Loaded: {len(G.nodes)} nodes, {len(G.edges)} edges")

for u, v, data in G.edges(data=True):
    for key in ("travel_time", "length", "risk_score"):
        if key in data:
            try:
                data[key] = float(data[key])
            except (ValueError, TypeError):
                data[key] = 0.0

def get_bounds(G, attr):
    values = [data.get(attr, 0) for _, _, data in G.edges(data=True)]
    return min(values), max(values)
 
 
bounds = {
    "travel_time": get_bounds(G, "travel_time"),
    "risk_score": get_bounds(G, "risk_score"),
    "length": get_bounds(G, "length"),
}
print("Normalization bounds:", bounds)
 
 
def normalize(value, bound):
    lo, hi = bound
    if hi == lo:
        return 0
    return (value - lo) / (hi - lo)
 
 
def expand_weights(speed_w, eco_w, safety_w):
    return {
        "travel_time": speed_w,
        "length": eco_w,
        "risk_score": safety_w,
    }
 
 
def apply_weights(G, weights, bounds):
    for u, v, data in G.edges(data=True):
        cost = 0
        for metric, weight in weights.items():
            if weight == 0:
                continue
            n = normalize(data.get(metric, 0), bounds[metric])
            cost += weight * n
        data["combined_cost"] = cost
 
 
def get_route(G, orig_point, dest_point, speed_w, eco_w, safety_w, bounds):
    weights = expand_weights(speed_w, eco_w, safety_w)
    apply_weights(G, weights, bounds)
 
    orig_node = ox.distance.nearest_nodes(G, orig_point[1], orig_point[0])
    dest_node = ox.distance.nearest_nodes(G, dest_point[1], dest_point[0])
 
    route = nx.shortest_path(G, orig_node, dest_node, weight="combined_cost")
    return route
 
 
def summarize_route(G, route, make, model, gas_type, congestion_sample_rate=5):
    totals = {"time_min": 0, "distance_km": 0, "fuel_usd": 0, "emissions_kg": 0, "avg_risk": 0}
    edge_count = 0
    congestion_factors = []
 
    for i in range(len(route) - 1):
        data = G.get_edge_data(route[i], route[i + 1])[0]
        base_time_min = data.get("travel_time", 0) / 60
 
        if i % congestion_sample_rate == 0:
            u_node = G.nodes[route[i]]
            lat, lon = u_node["y"], u_node["x"]
            factor = get_congestion_factor(lat, lon)
            congestion_factors.append(factor)
        else:
            factor = congestion_factors[-1] if congestion_factors else 1.0
 
        totals["time_min"] += base_time_min * factor
        totals["distance_km"] += data.get("length", 0) / 1000
        totals["avg_risk"] += float(data.get("risk_score", 0))
        edge_count += 1
 
    distance_miles = totals["distance_km"] * 0.621371
    fuel_cost, emissions = compute_fuel_cost_and_emissions(distance_miles, make, model, gas_type)
    totals["fuel_usd"] = fuel_cost
    totals["emissions_kg"] = emissions
 
    if edge_count > 0:
        totals["avg_risk"] /= edge_count
 
    avg_congestion = sum(congestion_factors) / len(congestion_factors) if congestion_factors else 1.0
    totals["avg_congestion_factor"] = avg_congestion
 
    return totals
 
 
def get_time_range(base_time_min, congestion_factor):
    best_case = base_time_min * min(congestion_factor * 0.85, congestion_factor)
    worst_case = base_time_min * congestion_factor
    return round(best_case), round(worst_case)
 
 
def compute_overall_score(summary, speed_w, eco_w, safety_w, route_bounds):
    n_time = normalize(summary["time_min"], route_bounds["time_min"])
    n_eco = normalize(summary["fuel_usd"] + summary["emissions_kg"], route_bounds["eco"])
    n_risk = normalize(summary["avg_risk"], route_bounds["risk"])
 
    weighted_cost = (speed_w * n_time) + (eco_w * n_eco) + (safety_w * n_risk)
    overall_score = round((1 - weighted_cost) * 100, 1)
    return overall_score
 
 
def compute_route_bounds(summaries):
    times = [s["time_min"] for s in summaries]
    ecos = [s["fuel_usd"] + s["emissions_kg"] for s in summaries]
    risks = [s["avg_risk"] for s in summaries]
 
    return {
        "time_min": (min(times), max(times)),
        "eco": (min(ecos), max(ecos)),
        "risk": (min(risks), max(risks)),
    }
 
 
def get_all_route_scores(G, orig_point, dest_point, speed_w, eco_w, safety_w, bounds, make, model, gas_type):
    """
    Returns the 4 fixed route CATEGORIES: fastest, greenest, safest, custom.
    Each is ONE route representing that priority.
    """
    presets = {
        "fastest": (1.0, 0.0, 0.0),
        "greenest": (0.0, 1.0, 0.0),
        "safest": (0.0, 0.0, 1.0),
        "custom": (speed_w, eco_w, safety_w),
    }
 
    routes = {}
    summaries = {}
    for name, (sw, ew, safw) in presets.items():
        route = get_route(G, orig_point, dest_point, sw, ew, safw, bounds)
        summary = summarize_route(G, route, make, model, gas_type)
        routes[name] = route
        summaries[name] = summary
 
    route_bounds = compute_route_bounds(list(summaries.values()))
 
    results = {}
    for name, summary in summaries.items():
        score = compute_overall_score(summary, speed_w, eco_w, safety_w, route_bounds)
        low, high = get_time_range(summary["time_min"], summary["avg_congestion_factor"])
        results[name] = {
            "route": routes[name],
            "summary": summary,
            "time_range": (low, high),
            "overall_score": score,
        }
 
    return results
 
def to_simple_digraph(G):
    simple_G = nx.DiGraph()
    for u, v, data in G.edges(data=True):
        cost = data.get("combined_cost", float("inf"))
        if simple_G.has_edge(u, v):
            if cost < simple_G[u][v]["combined_cost"]:
                simple_G[u][v]["combined_cost"] = cost
        else:
            simple_G.add_edge(u, v, combined_cost=cost)
    return simple_G
 
def get_multiple_routes(G, orig_point, dest_point, speed_w, eco_w, safety_w, bounds, k=5, timeout_seconds=8):
    weights = expand_weights(speed_w, eco_w, safety_w)
    apply_weights(G, weights, bounds)

    simple_G = to_simple_digraph(G)  # <-- convert here

    orig_node = ox.distance.nearest_nodes(G, orig_point[1], orig_point[0])
    dest_node = ox.distance.nearest_nodes(G, dest_point[1], dest_point[0])

    routes = []
    start_time = time_module.time()

    try:
        paths_gen = nx.shortest_simple_paths(simple_G, orig_node, dest_node, weight="combined_cost")
        for path in paths_gen:
            if time_module.time() - start_time > timeout_seconds:
                print(f"Stopped early after {len(routes)} routes (timeout)")
                break
            routes.append(path)
            if len(routes) >= k:
                break
    except nx.NetworkXNoPath:
        print("No path found between these points")
        return []

    return routes
 
 
def summarize_multiple_routes(G, routes, make, model, gas_type, speed_w, eco_w, safety_w):
    """
    Scores and ranks a list of route alternatives (from get_multiple_routes)
    so the user can pick from several real, distinct options -- not just
    one route per category.
    """
    if not routes:
        return []
 
    summaries = [summarize_route(G, route, make, model, gas_type) for route in routes]
    route_bounds = compute_route_bounds(summaries)
 
    results = []
    for route, summary in zip(routes, summaries):
        score = compute_overall_score(summary, speed_w, eco_w, safety_w, route_bounds)
        low, high = get_time_range(summary["time_min"], summary["avg_congestion_factor"])
        results.append({
            "route": route,
            "summary": summary,
            "time_range": (low, high),
            "overall_score": score,
        })
 
    results.sort(key=lambda r: r["overall_score"], reverse=True)
    return results
 
 
if __name__ == "__main__":
    test_orig_point = (37.7792, -122.4192)
    test_dest_point = (37.8024, -122.4058)
 
    # --- Step A: show the 4 category options (fastest/greenest/safest/custom) ---
    category_results = get_all_route_scores(
        G, test_orig_point, test_dest_point,
        speed_w=0.34, eco_w=0.33, safety_w=0.33,
        bounds=bounds, make="Toyota", model="Camry", gas_type="87"
    )
 
    print("=== Route categories ===")
    for name, r in category_results.items():
        s = r["summary"]
        print(f"\n--- {name} ---")
        print(f"Overall score: {r['overall_score']}/100")
        print(f"Time: {r['time_range'][0]}-{r['time_range'][1]} min")
        print(f"Distance: {s['distance_km']:.2f} km")
        print(f"Fuel cost: ${s['fuel_usd']:.2f}")
        print(f"Emissions: {s['emissions_kg']:.2f} kg CO2")
        print(f"Avg risk: {s['avg_risk']:.1f}")
 
    # --- Step B: user picked "custom" (or any category) -- now show multiple
    #     concrete route alternatives under that SAME weighting ---
    chosen_speed_w, chosen_eco_w, chosen_safety_w = 0.34, 0.33, 0.33  # e.g. "custom" weights
 
    alt_routes = get_multiple_routes(
        G, test_orig_point, test_dest_point,
        chosen_speed_w, chosen_eco_w, chosen_safety_w,
        bounds, k=5
    )
    print(f"\n\n=== {len(alt_routes)} alternative routes for the chosen priority ===")
 
    alt_results = summarize_multiple_routes(
        G, alt_routes, "Toyota", "Camry", "87",
        chosen_speed_w, chosen_eco_w, chosen_safety_w
    )
 
    for i, r in enumerate(alt_results, 1):
        s = r["summary"]
        print(f"\n--- Alternative {i} ---")
        print(f"Overall score: {r['overall_score']}/100")
        print(f"Time: {r['time_range'][0]}-{r['time_range'][1]} min")
        print(f"Distance: {s['distance_km']:.2f} km")
        print(f"Fuel cost: ${s['fuel_usd']:.2f}")
        print(f"Emissions: {s['emissions_kg']:.2f} kg CO2")
        print(f"Avg risk: {s['avg_risk']:.1f}")
 