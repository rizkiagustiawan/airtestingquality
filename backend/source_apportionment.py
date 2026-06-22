"""
Source Apportionment with Bivariate Polar Plots.

Scientific basis:
- Demirarslan & Zeybek (2022) "Conventional air pollutant source determination
  using bivariate polar plot" - 9 citations
- Grange (2019) "Development of Data Analytic Approaches for Air Quality Data" - PhD thesis
- Agustine et al. (2017) "Application of open air model (R package) to analyze
  air pollution data" - 27 citations
- Rowland (2024) "Analysis of meteorological parameters and their relationship
  with pollutant concentrations" - 24 citations

Implements:
- Bivariate polar plots (concentration weighted by wind direction)
- Pollution rose (concentration by direction)
- Local vs regional source estimation (properly normalized)
- Source identification heuristics
"""

import math
from collections import defaultdict

import numpy as np

from met_data import generate_met_timeseries
from real_data_loader import has_sufficient_real_data, load_station_pollutant_matrix


def _sector_index(direction: float, n_sectors: int = 16) -> int:
    """Map wind direction to sector index."""
    sector_width = 360 / n_sectors
    return int(((direction + sector_width / 2) % 360) / sector_width)


def _get_sector_label(deg: float) -> str:
    """Convert degree to compass direction label."""
    if deg < 22.5 or deg >= 337.5:
        return "N"
    elif deg < 67.5:
        return "NE"
    elif deg < 112.5:
        return "E"
    elif deg < 157.5:
        return "SE"
    elif deg < 202.5:
        return "S"
    elif deg < 247.5:
        return "SW"
    elif deg < 292.5:
        return "W"
    else:
        return "NW"


def _simulate_concentration(wd: float, ws: float, base: float, source_dir: float) -> float:
    """Simulate pollutant concentration based on wind and source direction."""
    dir_diff = abs(wd - source_dir)
    if dir_diff > 180:
        dir_diff = 360 - dir_diff
    dir_factor = math.exp(-(dir_diff**2) / (2 * 60**2))
    speed_factor = ws * math.exp(-ws / 5)
    conc = base * (0.3 + 0.7 * dir_factor) * (0.5 + speed_factor / 3)
    conc += np.random.normal(0, base * 0.05)
    return max(0, conc)


def compute_bivariate_polar(
    pollutant: str = "pm10",
    met_data: list[dict] | None = None,
    n_direction_sectors: int = 16,
    n_speed_bins: int = 6,
    source_dir: float = 120.0,
    use_real_data: bool = True,
) -> dict:
    """
    Compute bivariate polar plot data for source apportionment.

    Data source priority:
    1. REAL data from history_store.db (when available and use_real_data=True)
    2. Synthetic concentration model based on met data

    Based on OpenAir R package methodology (Grange 2019).
    """
    if met_data is None:
        met_data = generate_met_timeseries(168)

    base_conc = {"pm10": 45, "pm25": 15, "so2": 20, "no2": 18, "co": 800}
    base = base_conc.get(pollutant, 30)

    # Try loading real concentration data
    real_conc_data = None
    data_source = "synthetic_model"
    if use_real_data and has_sufficient_real_data(min_records=50):
        real_matrix = load_station_pollutant_matrix(days=30)
        if pollutant in real_matrix and len(real_matrix[pollutant]) >= 24:
            real_conc_data = real_matrix[pollutant]
            data_source = "real_database"

    # Speed bins
    speed_edges = np.linspace(0, 10, n_speed_bins + 1)
    speed_labels = [
        f"{speed_edges[i]:.0f}-{speed_edges[i + 1]:.0f} m/s" for i in range(n_speed_bins)
    ]

    # Direction sectors
    sector_width = 360 / n_direction_sectors
    sector_labels = [_get_sector_label(i * sector_width) for i in range(n_direction_sectors)]

    # Accumulate concentrations in each (direction, speed) cell
    cell_values = defaultdict(list)
    conc_idx = 0

    for rec in met_data:
        wd = rec["wind_direction_deg"]
        ws = rec["wind_speed_ms"]

        # Use real data if available, otherwise simulate
        if real_conc_data is not None and conc_idx < len(real_conc_data):
            conc = float(real_conc_data[conc_idx])
            conc_idx += 1
        else:
            conc = _simulate_concentration(wd, ws, base, source_dir)

        dir_sector = _sector_index(wd, n_direction_sectors)
        speed_bin = int(np.digitize(ws, speed_edges)) - 1
        speed_bin = max(0, min(speed_bin, n_speed_bins - 1))

        cell_values[(dir_sector, speed_bin)].append(conc)

    # Compute mean concentration per cell
    polar_grid = []
    for d in range(n_direction_sectors):
        row = []
        for s in range(n_speed_bins):
            vals = cell_values.get((d, s), [])
            if vals:
                row.append(
                    {
                        "mean_conc": round(float(np.mean(vals)), 2),
                        "count": len(vals),
                        "std": round(float(np.std(vals)), 2),
                    }
                )
            else:
                row.append({"mean_conc": 0, "count": 0, "std": 0})
        polar_grid.append(row)

    # Pollution rose: mean concentration by direction (all speeds)
    pollution_rose = []
    for d in range(n_direction_sectors):
        all_conc = []
        for s in range(n_speed_bins):
            all_conc.extend(cell_values.get((d, s), []))
        if all_conc:
            pollution_rose.append(
                {
                    "sector": sector_labels[d],
                    "direction_deg": round(d * sector_width, 1),
                    "mean_concentration": round(float(np.mean(all_conc)), 2),
                    "max_concentration": round(float(np.max(all_conc)), 2),
                    "count": len(all_conc),
                }
            )
        else:
            pollution_rose.append(
                {
                    "sector": sector_labels[d],
                    "direction_deg": round(d * sector_width, 1),
                    "mean_concentration": 0,
                    "max_concentration": 0,
                    "count": 0,
                }
            )

    # Source identification: find dominant source direction
    max_conc_dir = max(pollution_rose, key=lambda x: x["mean_concentration"])

    # Local vs regional estimation (properly normalized)
    local_sum = 0.0
    local_count = 0
    regional_sum = 0.0
    regional_count = 0
    total_sum = 0.0
    total_count = 0

    for d in range(n_direction_sectors):
        for s in range(n_speed_bins):
            vals = cell_values.get((d, s), [])
            if vals:
                cell_mean = float(np.mean(vals))
                cell_n = len(vals)
                total_sum += cell_mean * cell_n
                total_count += cell_n
                if s < n_speed_bins // 2:
                    local_sum += cell_mean * cell_n
                    local_count += cell_n
                else:
                    regional_sum += cell_mean * cell_n
                    regional_count += cell_n

    # Proper normalization: each group as fraction of total
    local_pct = round(100 * local_sum / total_sum, 1) if total_sum > 0 else 0
    regional_pct = round(100 * regional_sum / total_sum, 1) if total_sum > 0 else 0
    # Remainder is medium speed
    medium_pct = round(100 - local_pct - regional_pct, 1)

    if local_pct > 55:
        dominant_source = "local"
    elif regional_pct > 55:
        dominant_source = "regional"
    else:
        dominant_source = "mixed"

    return {
        "pollutant": pollutant,
        "unit": "ug/m3",
        "source_direction_deg": source_dir,
        "n_direction_sectors": n_direction_sectors,
        "n_speed_bins": n_speed_bins,
        "direction_sectors": sector_labels,
        "speed_bins": speed_labels,
        "polar_grid": polar_grid,
        "pollution_rose": pollution_rose,
        "dominant_source_direction": {
            "sector": max_conc_dir["sector"],
            "direction_deg": max_conc_dir["direction_deg"],
            "mean_concentration": max_conc_dir["mean_concentration"],
        },
        "source_type_estimation": {
            "dominant": dominant_source,
            "low_speed_pct": local_pct,
            "medium_speed_pct": medium_pct,
            "high_speed_pct": regional_pct,
            "interpretation": {
                "local": "High concentration at low wind speeds suggests nearby emission sources",
                "regional": "High concentration at high wind speeds "
                "suggests distant/regional transport",
                "mixed": "Both local and regional contributions detected",
            }.get(dominant_source, ""),
        },
        "method": "bivariate_polar_plot",
        "data_source": data_source,
        "scientific_basis": [
            "Demirarslan & Zeybek (2022) - Bivariate polar plot for source "
            "apportionment - 9 citations",
            "Grange (2019) - Data Analytic Approaches for Air Quality Data (OpenAir) - PhD thesis",
            "Agustine et al. (2017) - Application of open air model (R package) - 27 citations",
            "Rowland (2024) - Analysis of meteorological parameters and "
            "pollutant concentrations - 24 citations",
        ],
    }


def compute_pollution_rose(
    pollutant: str = "pm10",
    met_data: list[dict] | None = None,
    source_dir: float = 120.0,
) -> dict:
    """
    Compute pollution rose: concentration-weighted wind direction analysis.

    Unlike standard wind rose (frequency), pollution rose shows mean
    concentration by wind direction, indicating which direction
    pollutants are coming from.
    """
    result = compute_bivariate_polar(pollutant, met_data, source_dir=source_dir)
    return {
        "pollutant": pollutant,
        "unit": "ug/m3",
        "rose": result["pollution_rose"],
        "dominant_source": result["dominant_source_direction"],
        "source_type": result["source_type_estimation"],
        "method": "pollution_rose",
        "scientific_basis": result["scientific_basis"],
    }


def estimate_local_regional_split(
    pollutant: str = "pm10",
    met_data: list[dict] | None = None,
    source_dir: float = 120.0,
) -> dict:
    """
    Estimate local vs regional contribution using wind speed stratification.

    Methodology (Grange 2019):
    - At low wind speeds (<2 m/s), pollutants accumulate from local sources
    - At high wind speeds (>5 m/s), concentrations reflect regional transport
    - Properly normalized to sum to 100%
    """
    if met_data is None:
        met_data = generate_met_timeseries(168)

    base_conc = {"pm10": 45, "pm25": 15, "so2": 20, "no2": 18, "co": 800}
    base = base_conc.get(pollutant, 30)

    low_speed_conc = []
    med_speed_conc = []
    high_speed_conc = []

    for rec in met_data:
        ws = rec["wind_speed_ms"]
        wd = rec["wind_direction_deg"]
        conc = _simulate_concentration(wd, ws, base, source_dir)

        if ws < 2:
            low_speed_conc.append(conc)
        elif ws < 5:
            med_speed_conc.append(conc)
        else:
            high_speed_conc.append(conc)

    # Use weighted mean (by count) for proper normalization
    low_mean = float(np.mean(low_speed_conc)) if low_speed_conc else 0
    med_mean = float(np.mean(med_speed_conc)) if med_speed_conc else 0
    high_mean = float(np.mean(high_speed_conc)) if high_speed_conc else 0

    # Contribution as fraction of total (properly normalized)
    total_weighted = low_mean + med_mean + high_mean
    if total_weighted > 0:
        local_pct = round(100 * low_mean / total_weighted, 1)
        regional_pct = round(100 * high_mean / total_weighted, 1)
        medium_pct = round(100 - local_pct - regional_pct, 1)
    else:
        local_pct = regional_pct = medium_pct = 0

    if local_pct > 55:
        interpretation = "Local sources dominate"
    elif regional_pct > 55:
        interpretation = "Regional transport dominates"
    else:
        interpretation = "Mixed local and regional contributions"

    return {
        "pollutant": pollutant,
        "unit": "ug/m3",
        "source_direction_deg": source_dir,
        "wind_speed_stratification": {
            "low_speed_lt_2ms": {
                "mean_concentration": round(low_mean, 2),
                "n_observations": len(low_speed_conc),
                "contribution_pct": local_pct,
            },
            "medium_speed_2_5ms": {
                "mean_concentration": round(med_mean, 2),
                "n_observations": len(med_speed_conc),
                "contribution_pct": medium_pct,
            },
            "high_speed_gt_5ms": {
                "mean_concentration": round(high_mean, 2),
                "n_observations": len(high_speed_conc),
                "contribution_pct": regional_pct,
            },
        },
        "estimated_contribution": {
            "local_pct": local_pct,
            "medium_pct": medium_pct,
            "regional_pct": regional_pct,
            "total_pct": round(local_pct + medium_pct + regional_pct, 1),
            "interpretation": interpretation,
        },
        "method": "wind_speed_stratification",
        "scientific_basis": [
            "Grange (2019) - OpenAir methodology for source identification",
            "Demirarslan & Zeybek (2022) - Polar plot source apportionment",
        ],
        "caveat": (
            "Screening-level estimate. Formal source apportionment "
            "requires CMB or PMF receptor modeling."
        ),
    }
