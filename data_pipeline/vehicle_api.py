import requests
 
BASE_URL = "https://www.fueleconomy.gov/ws/rest/vehicle"
 
 
def get_models(make, year=2023):
    url = f"{BASE_URL}/menu/model"
    params = {"make": make, "year": year}
    try:
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        models = data.get("menuItem", [])
        if isinstance(models, dict):
            models = [models]
        return [m["value"] for m in models]
    except Exception:
        return []
 
 
def get_vehicle_mpg(make, model, year=2023):
    url = f"{BASE_URL}/menu/options"
    params = {"make": make, "model": model, "year": year}
    try:
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        options = data.get("menuItem", [])
        if isinstance(options, dict):
            options = [options]
        if not options:
            return None
 
        vehicle_id = options[0]["value"]
        detail_url = f"{BASE_URL}/{vehicle_id}"
        detail_resp = requests.get(detail_url, params={"format": "json"}, timeout=5)
        detail_resp.raise_for_status()
        detail_data = detail_resp.json()
 
        return {
            "combined_mpg": detail_data.get("comb08"),
            "kwh_per_100mi": detail_data.get("kwh100M"),
            "fuel_type": detail_data.get("fuelType1"),
        }
    except Exception:
        return None
 
 
if __name__ == "__main__":
    models = get_models("Toyota")
    print(f"Toyota models found: {len(models)}")
    print(models[:5])
 
    result = get_vehicle_mpg("Toyota", "Camry")
    print("Camry lookup result:", result)
 
    bad_result = get_models("NotARealMake")
    print("Bad make result (should be empty list, not a crash):", bad_result)