import random
from datetime import datetime

def fetch_indonesia_air_quality():
    """
    Optimized data generator locked to Nusa Tenggara Barat (NTB) stations.
    Provides instant, reliable data for the portfolio dashboard without 3rd-party API reliance.
    """
    now_iso = datetime.utcnow().isoformat() + "Z"
    
    # Base stations in NTB
    stations = [
        {
            "id": "ntb-01",
            "location": "Sumbawa Barat (AMNT Area)",
            "city": "Sumbawa Barat",
            "latitude": -8.8250,
            "longitude": 116.8400,
            "base_metrics": {"pm25": 12, "pm10": 45, "so2": 15, "no2": 10, "co": 800, "o3": 25}
        },
        {
            "id": "ntb-02",
            "location": "Mataram Central",
            "city": "Mataram",
            "latitude": -8.5833,
            "longitude": 116.1167,
            "base_metrics": {"pm25": 35, "pm10": 60, "so2": 20, "no2": 25, "co": 1200, "o3": 40}
        },
        {
            "id": "ntb-03",
            "location": "Bima Regional",
            "city": "Bima",
            "latitude": -8.4667,
            "longitude": 118.7167,
            "base_metrics": {"pm25": 22, "pm10": 50, "so2": 10, "no2": 15, "co": 950, "o3": 30}
        },
        {
            "id": "ntb-04",
            "location": "Lombok International Airport",
            "city": "Lombok Tengah",
            "latitude": -8.7610,
            "longitude": 116.2750,
            "base_metrics": {"pm25": 18, "pm10": 40, "so2": 12, "no2": 18, "co": 850, "o3": 35}
        }
    ]
    
    parsed_locations = []
    
    for st in stations:
        metrics = {}
        # Ensure the type-checker knows base_metrics is a dictionary
        base_metrics = st.get("base_metrics", {})
        if isinstance(base_metrics, dict):
            for param, base_val in base_metrics.items():
                if isinstance(base_val, (int, float)):
                    # Randomize by +/- 15%
                    variation = float(base_val) * 0.15
                    val = float(base_val) + random.uniform(-variation, variation)
                    # Python's round with ndigits sometimes fails in strict type checkers
                    metrics[param] = float(f"{val:.2f}")
            
        parsed_locations.append({
            "id": st["id"],
            "location": st["location"],
            "city": st["city"],
            "latitude": st["latitude"],
            "longitude": st["longitude"],
            "last_updated": now_iso,
            "measurements": metrics
        })
        
    return parsed_locations
