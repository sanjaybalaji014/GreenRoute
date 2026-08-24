from vehicle_api import get_vehicle_mpg

ELECTRICITY_PRICE_PER_KWH = 0.42
GRID_EMISSIONS_KG_PER_KWH = 0.185

GAS_PRICE_BY_TYPE = {
    "87": 5.7221,
    "89": 5.9725,
    "91": 6.1340,
    "diesel": 7.3102
}

EMISSIONS_KG_PER_GALLON = {
    "87": 8.10,
    "89": 8.10,
    "91": 8.10,
    "diesel": 10.19
}

FALLBACK_MPG = 27.2


def compute_fuel_cost_and_emissions(distance_miles, make, model, gas_type):
    try:
        vehicle_info = get_vehicle_mpg(make, model)
    except Exception:
        vehicle_info = None

    if vehicle_info and vehicle_info.get("kwh_per_100mi"):
        kwh_per_mile = vehicle_info["kwh_per_100mi"] / 100
        kwh_used = distance_miles * kwh_per_mile
        fuel_cost = kwh_used * ELECTRICITY_PRICE_PER_KWH
        emissions = kwh_used * GRID_EMISSIONS_KG_PER_KWH
        return fuel_cost, emissions

    if vehicle_info and vehicle_info.get("combined_mpg"):
        mpg = vehicle_info["combined_mpg"]
    else:
        mpg = FALLBACK_MPG

    gallons_used = distance_miles / mpg

    price_per_gallon = GAS_PRICE_BY_TYPE.get(gas_type, GAS_PRICE_BY_TYPE["87"])
    fuel_cost = gallons_used * price_per_gallon

    emissions_per_gallon = EMISSIONS_KG_PER_GALLON.get(gas_type, EMISSIONS_KG_PER_GALLON["87"])
    emissions = gallons_used * emissions_per_gallon

    return fuel_cost, emissions
