import requests
import os

TOMTOM_API_KEY = os.environ.get("TOMTOM_API_KEY")

def get_congestion_factor(lat, lon):
    url = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
    params = {"point": f"{lat},{lon}", "key": TOMTOM_API_KEY}
    try:
        resp = requests.get(url, params=params, timeout=3)
        resp.raise_for_status()
        data = resp.json()["flowSegmentData"]
        free_flow = data["freeFlowSpeed"]
        current = data["currentSpeed"]
        return free_flow / max(current, 1)
    except Exception:
        return 1.0