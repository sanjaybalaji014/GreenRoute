import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import osmnx as ox
import networkx as nx

crash_url = "https://data.sfgov.org/resource/ubvf-ztfx.csv?$limit=50000"
crashes_df = pd.read_csv(crash_url)
print(f"Crashes loaded: {len(crashes_df)} rows")

crashes_df = crashes_df.dropna(subset=["tb_latitude", "tb_longitude"])
crashes_gdf = gpd.GeoDataFrame(
    crashes_df,
    geometry=[Point(xy) for xy in zip(crashes_df["tb_longitude"], crashes_df["tb_latitude"])],
    crs = "EPSG:4326"
)

print(f"Usable crash points: {len(crashes_gdf)}")

G = ox.load_graphml("data/city_graph.graphml")
edges_gdf = ox.graph_to_gdfs(G, nodes=False, edges=True)
print(f"Graph loaded: {len(edges_gdf)} edges")

edges_proj = edges_gdf.to_crs(epsg=3857)
crashes_proj = crashes_gdf.to_crs(epsg=3857)

def compute_risk_score(edge_geom, highway_type, speed_kph, nearby_crashes_df):
    score = 0
    severity_weight = 0
    for _, crash in nearby_crashes_df.iterrows():
        if crash.get("number_killed", 0) and crash["number_killed"] > 0:
            severity_weight += 10
        elif crash.get("number_injured" , 0) and crash["number_injured"] > 0:
            severity_weight += 4
        else:
            severity_weight += 1
    score += min(severity_weight, 50)

    if highway_type in ("primary", "trunk", "secondary"):
        score += 15
    if speed_kph and speed_kph > 50:
        score += 20
    return min(score, 100)

risk_scores = []
BUFFER_METERS = 30

for idk, row in edges_proj.iterrows():
    highway = row.get("highway", "unknown")
    if isinstance(highway, list):
        highway = highway[0]
    speed = row.get("speed_kph", 40)

    buffer = row.geometry.buffer(BUFFER_METERS)
    nearby_crashes = crashes_proj[crashes_proj.geometry.within(buffer)]

    risk_scores.append(compute_risk_score(row.geometry, highway, speed, nearby_crashes))

edges_gdf["risk_score"] = risk_scores
print("Risk scores computed")
print(edges_gdf["risk_score"].describe())

for (u, v, key), risk in zip(edges_gdf.index, edges_gdf["risk_score"]):
    G[u][v][key]["risk_score"] = risk

ox.save_graphml(G, "data/city_graph.graphml")
print("Graph updated with risk scores and saved to data/city_graph_with_metrics_and_risk.graphml")