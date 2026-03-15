"""
Emission Sources for PT AMMAN Mineral NTB Mining Complex.
Defines all major emission sources with coordinates, types, and emission rates.
"""

# ------------------------------------------------------------------
# PT AMMAN Mineral – Sumbawa Mining Complex Emission Sources
# Coordinates are realistic approximate locations in Sumbawa Barat.
# ------------------------------------------------------------------

EMISSION_SOURCES = [
    {
        "id": "open-pit",
        "name": "Open Pit Mine",
        "type": "area",
        "icon": "⛏️",
        "lat": -8.8300,
        "lon": 116.8500,
        "elevation_m": 350,
        "description": "Active copper-gold open pit excavation area",
        "area_m2": 500000,
        "emissions": {  # g/s
            "pm10": 8.5,
            "pm25": 2.1,
            "tsp": 15.0,
            "so2": 0.0,
            "nox": 0.5,
            "co": 1.2
        },
        "stack_height_m": 0,
        "color": "#D97706"
    },
    {
        "id": "crusher-plant",
        "name": "Crusher & Grinding Plant",
        "type": "area",
        "icon": "🏗️",
        "lat": -8.8220,
        "lon": 116.8600,
        "elevation_m": 280,
        "description": "Primary and secondary ore crushing facility",
        "area_m2": 20000,
        "emissions": {
            "pm10": 12.0,
            "pm25": 3.5,
            "tsp": 22.0,
            "so2": 0.0,
            "nox": 0.3,
            "co": 0.8
        },
        "stack_height_m": 0,
        "color": "#92400E"
    },
    {
        "id": "smelter-stack",
        "name": "Smelter Stack",
        "type": "point",
        "icon": "🏭",
        "lat": -8.8100,
        "lon": 116.8750,
        "elevation_m": 120,
        "description": "Copper smelter main exhaust stack (80m tall)",
        "area_m2": 0,
        "emissions": {
            "pm10": 2.5,
            "pm25": 1.8,
            "tsp": 3.0,
            "so2": 25.0,
            "nox": 8.5,
            "co": 5.2
        },
        "stack_height_m": 80,
        "stack_diameter_m": 3.5,
        "exit_velocity_ms": 18.0,
        "exit_temp_k": 423,
        "color": "#DC2626"
    },
    {
        "id": "hauling-road",
        "name": "Hauling Road Network",
        "type": "line",
        "icon": "🚛",
        "lat": -8.8200,
        "lon": 116.8550,
        "elevation_m": 200,
        "description": "Heavy vehicle haul road (approx 15 km network)",
        "length_m": 15000,
        "area_m2": 150000,
        "emissions": {
            "pm10": 18.0,
            "pm25": 4.0,
            "tsp": 35.0,
            "so2": 0.0,
            "nox": 3.5,
            "co": 8.0
        },
        "stack_height_m": 0,
        "color": "#F59E0B"
    },
    {
        "id": "stockpile",
        "name": "Ore Stockpile Area",
        "type": "area",
        "icon": "📦",
        "lat": -8.8180,
        "lon": 116.8420,
        "elevation_m": 250,
        "description": "Ore and waste rock stockpile with wind erosion",
        "area_m2": 80000,
        "emissions": {
            "pm10": 5.0,
            "pm25": 1.2,
            "tsp": 10.0,
            "so2": 0.0,
            "nox": 0.0,
            "co": 0.0
        },
        "stack_height_m": 0,
        "color": "#78716C"
    },
    {
        "id": "power-plant",
        "name": "LNG Power Plant",
        "type": "point",
        "icon": "⚡",
        "lat": -8.8050,
        "lon": 116.8680,
        "elevation_m": 50,
        "description": "450 MW Combined Cycle LNG power generation",
        "area_m2": 0,
        "emissions": {
            "pm10": 0.8,
            "pm25": 0.5,
            "tsp": 1.0,
            "so2": 2.0,
            "nox": 12.0,
            "co": 3.5
        },
        "stack_height_m": 60,
        "stack_diameter_m": 2.8,
        "exit_velocity_ms": 15.0,
        "exit_temp_k": 393,
        "color": "#7C3AED"
    },
    {
        "id": "port-facility",
        "name": "Port & Loading Facility",
        "type": "area",
        "icon": "🚢",
        "lat": -8.7950,
        "lon": 116.8900,
        "elevation_m": 5,
        "description": "Concentrate loading and ship berthing area",
        "area_m2": 40000,
        "emissions": {
            "pm10": 3.0,
            "pm25": 0.8,
            "tsp": 6.0,
            "so2": 0.5,
            "nox": 1.5,
            "co": 2.0
        },
        "stack_height_m": 0,
        "color": "#0891B2"
    }
]

# Sensitive receptor locations around the mining complex
RECEPTORS = [
    {"id": "desa-maluk", "name": "Desa Maluk", "lat": -8.7900, "lon": 116.8200, "type": "settlement", "population": 5200},
    {"id": "desa-sekongkang", "name": "Desa Sekongkang", "lat": -8.8400, "lon": 116.8100, "type": "settlement", "population": 3800},
    {"id": "desa-tongo", "name": "Desa Tongo", "lat": -8.8500, "lon": 116.8700, "type": "settlement", "population": 2100},
    {"id": "pesisir-utara", "name": "Pesisir Utara", "lat": -8.7700, "lon": 116.8600, "type": "coastal", "population": 0},
    {"id": "kawasan-hutan", "name": "Kawasan Hutan Lindung", "lat": -8.8600, "lon": 116.8400, "type": "protected_forest", "population": 0},
]


def get_emission_sources():
    """Return all emission source definitions."""
    return EMISSION_SOURCES


def get_receptors():
    """Return all receptor locations."""
    return RECEPTORS


def get_source_by_id(source_id: str):
    """Get a single source by ID."""
    for src in EMISSION_SOURCES:
        if src["id"] == source_id:
            return src
    return None


def get_total_emissions():
    """Calculate total emissions from all sources (g/s)."""
    import typing
    totals: dict[str, float] = {}
    for src in EMISSION_SOURCES:
        emissions = typing.cast(dict[str, float], src.get("emissions", {}))
        for pollutant, rate in emissions.items():
            totals[pollutant] = totals.get(pollutant, 0) + rate
    return totals
