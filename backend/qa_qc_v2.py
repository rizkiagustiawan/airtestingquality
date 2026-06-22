"""
QA/QC Pipeline v2: Automated Quality Control based on SaQC Framework.

Scientific basis:
- Schmidt et al. (2023) "System for automated Quality Control (SaQC)" - 44 citations
- Faybishenko et al. (2022) "Challenging problems of QA/QC of meteorological time series data" - 65 citations
- D'Amore et al. (2015) "Data quality through a web-based QA/QC system" - 46 citations

Implements enhanced quality control checks following the SaQC framework:
- Range check (physical bounds)
- Spike detection (Z-score based)
- Drift detection (rolling mean comparison)
- Flatline detection (stuck sensor)
- Temporal consistency (rate of change)
- Cross-pollutant consistency (PM2.5 < PM10)
"""

from copy import deepcopy

import numpy as np

# Physical bounds per WMO/EPA standards (µg/m³)
RANGE_RULES = {
    "pm25": (0.0, 500.0),
    "pm10": (0.0, 600.0),
    "so2": (0.0, 1200.0),
    "no2": (0.0, 3000.0),
    "co": (0.0, 50000.0),
    "o3": (0.0, 1000.0),
}

# WMO flag codes
FLAG_CODES = {
    "missing": "MISSING",
    "non_numeric": "NON_NUMERIC",
    "out_of_range": "OUT_OF_RANGE",
    "spike": "SPIKE",
    "flatline": "FLATLINE",
    "drift": "DRIFT",
    "rate_of_change": "RATE_OF_CHANGE",
    "cross_pollutant": "CROSS_POLLUTANT",
    "valid": "VALID",
}

# Maximum plausible rate of change per hour (µg/m³/hour)
MAX_RATE_OF_CHANGE = {
    "pm25": 50.0,
    "pm10": 100.0,
    "so2": 200.0,
    "no2": 300.0,
    "co": 5000.0,
    "o3": 150.0,
}


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float))


def _check_range(value: float, pollutant: str) -> dict | None:
    """Physical bounds validation per SaQC range check."""
    if pollutant not in RANGE_RULES:
        return None
    min_val, max_val = RANGE_RULES[pollutant]
    if value < min_val or value > max_val:
        return {
            "code": FLAG_CODES["out_of_range"],
            "severity": "critical",
            "detail": f"Value {value} outside physical bounds [{min_val}, {max_val}]",
        }
    return None


def _check_spike(value: float, history: list[float], threshold_sigma: float = 3.0) -> dict | None:
    """
    Z-score based spike detection.

    Based on SaQC framework (Schmidt et al. 2023):
    Spike detected when |x - μ| > nσ where n=3 (default).
    More robust than fixed percentage threshold.
    """
    if len(history) < 3:
        return None

    arr = np.array(history)
    mean = np.mean(arr)
    std = np.std(arr)

    if std < 1e-6:
        return None

    z_score = abs(value - mean) / std
    if z_score > threshold_sigma:
        return {
            "code": FLAG_CODES["spike"],
            "severity": "warning",
            "detail": f"Z-score {z_score:.2f} exceeds threshold {threshold_sigma}",
            "z_score": round(z_score, 2),
        }
    return None


def _check_flatline(history: list[float], min_repeats: int = 5) -> dict | None:
    """
    Flatline/stuck sensor detection.

    Based on SaQC framework: detects when sensor reports identical values
    consecutively, indicating malfunction.
    """
    if len(history) < min_repeats:
        return None

    recent = history[-min_repeats:]
    if len(set(recent)) == 1:
        return {
            "code": FLAG_CODES["flatline"],
            "severity": "warning",
            "detail": f"Same value repeated {min_repeats} times (stuck sensor suspected)",
        }
    return None


def _check_drift(history: list[float], window_short: int = 6, window_long: int = 24) -> dict | None:
    """
    Sensor drift detection.

    Based on Faybishenko et al. (2022): compares short-term and long-term
    rolling means. Significant divergence indicates sensor drift.
    """
    if len(history) < window_long:
        return None

    arr = np.array(history)
    mean_short = np.mean(arr[-window_short:])
    mean_long = np.mean(arr[-window_long:])

    if mean_long < 1e-6:
        return None

    drift_ratio = abs(mean_short - mean_long) / mean_long
    if drift_ratio > 0.5:  # 50% divergence
        return {
            "code": FLAG_CODES["drift"],
            "severity": "warning",
            "detail": f"Drift detected: short/long mean ratio {drift_ratio:.2f}",
            "drift_ratio": round(drift_ratio, 3),
        }
    return None


def _check_rate_of_change(value: float, previous: float | None, pollutant: str) -> dict | None:
    """
    Temporal consistency: rate of change check.

    Based on SaQC framework: physically implausible rate of change
    indicates measurement error.
    """
    if previous is None or pollutant not in MAX_RATE_OF_CHANGE:
        return None

    roc = abs(value - previous)
    max_roc = MAX_RATE_OF_CHANGE[pollutant]

    if roc > max_roc:
        return {
            "code": FLAG_CODES["rate_of_change"],
            "severity": "warning",
            "detail": f"Rate of change {roc:.1f} exceeds max plausible {max_roc} µg/m³/hr",
        }
    return None


def _check_cross_pollutant(measurements: dict) -> list[dict]:
    """
    Cross-pollutant consistency check.

    Known physical relationship: PM2.5 ≤ PM10 (PM2.5 is a subset of PM10).
    Violation indicates measurement error.
    """
    flags = []
    pm25 = measurements.get("pm25")
    pm10 = measurements.get("pm10")

    if _is_number(pm25) and _is_number(pm10):
        if pm25 > pm10:
            flags.append(
                {
                    "code": FLAG_CODES["cross_pollutant"],
                    "severity": "critical",
                    "detail": f"PM2.5 ({pm25}) > PM10 ({pm10}): physically impossible",
                    "pollutants": ["pm25", "pm10"],
                }
            )

    return flags


def run_qaqc_v2_on_station(
    station: dict,
    prev_measurements: dict | None = None,
    history_by_pollutant: dict[str, list[float]] | None = None,
) -> dict:
    """
    Enhanced QA/QC per station following SaQC framework.

    Checks applied (in order):
    1. Missing/non-numeric check
    2. Range check (physical bounds)
    3. Spike detection (Z-score)
    4. Flatline detection
    5. Drift detection
    6. Rate of change
    7. Cross-pollutant consistency
    """
    prev = prev_measurements or {}
    history = history_by_pollutant or {}
    raw = deepcopy(station.get("measurements", {}))
    cleaned = {}
    flags = []

    for pollutant, (min_val, max_val) in RANGE_RULES.items():
        value = raw.get(pollutant)

        # Check 1: Missing
        if value is None:
            flags.append(
                {
                    "pollutant": pollutant,
                    "code": FLAG_CODES["missing"],
                    "severity": "info",
                    "detail": "No value in input payload",
                }
            )
            continue

        # Check 2: Non-numeric
        if not _is_number(value):
            flags.append(
                {
                    "pollutant": pollutant,
                    "code": FLAG_CODES["non_numeric"],
                    "severity": "critical",
                    "detail": "Value is not numeric",
                }
            )
            continue

        value = float(value)

        # Check 3: Range
        range_flag = _check_range(value, pollutant)
        if range_flag:
            range_flag["pollutant"] = pollutant
            flags.append(range_flag)
            continue

        # Check 4: Spike (Z-score based)
        pollutant_history = history.get(pollutant, [])
        spike_flag = _check_spike(value, pollutant_history)
        if spike_flag:
            spike_flag["pollutant"] = pollutant
            flags.append(spike_flag)

        # Check 5: Flatline
        flatline_flag = _check_flatline(pollutant_history + [value])
        if flatline_flag:
            flatline_flag["pollutant"] = pollutant
            flags.append(flatline_flag)

        # Check 6: Drift
        drift_flag = _check_drift(pollutant_history + [value])
        if drift_flag:
            drift_flag["pollutant"] = pollutant
            flags.append(drift_flag)

        # Check 7: Rate of change
        previous = prev.get(pollutant)
        roc_flag = _check_rate_of_change(value, previous, pollutant)
        if roc_flag:
            roc_flag["pollutant"] = pollutant
            flags.append(roc_flag)

        cleaned[pollutant] = value

    # Check 8: Cross-pollutant consistency
    cross_flags = _check_cross_pollutant(cleaned)
    flags.extend(cross_flags)

    # Quality score: weighted by severity
    severity_weights = {"critical": 3, "warning": 1, "info": 0.5}
    total_penalty = sum(severity_weights.get(f["severity"], 0) for f in flags)
    max_possible = len(RANGE_RULES) * 3  # worst case: all critical
    quality_score = round(max(0, 100 - (total_penalty / max_possible) * 100), 1)

    valid_count = len(cleaned)
    total_count = len(RANGE_RULES)
    valid_rate = round((valid_count / total_count) * 100, 2) if total_count else 0.0

    out = deepcopy(station)
    out["measurements_raw"] = raw
    out["measurements"] = cleaned
    out["qa_qc"] = {
        "valid_count": valid_count,
        "total_count": total_count,
        "valid_rate_pct": valid_rate,
        "quality_score": quality_score,
        "flags": flags,
        "flag_summary": {
            code: len([f for f in flags if f["code"] == code])
            for code in FLAG_CODES.values()
            if any(f["code"] == code for f in flags)
        },
    }
    return out


def run_qaqc_v2(
    stations: list[dict],
    previous_by_station: dict[str, dict] | None = None,
    history_by_station: dict[str, dict[str, list[float]]] | None = None,
) -> tuple[list[dict], dict]:
    """
    Run enhanced QA/QC on all stations.

    Returns: (processed_stations, summary)
    """
    processed = []
    total_valid = 0
    total_expected = 0
    total_flags = 0
    all_quality_scores = []
    prev_map = previous_by_station or {}
    history_map = history_by_station or {}

    for station in stations:
        station_id = str(station.get("id", ""))
        checked = run_qaqc_v2_on_station(
            station,
            prev_measurements=prev_map.get(station_id),
            history_by_pollutant=history_map.get(station_id),
        )
        processed.append(checked)
        qa = checked["qa_qc"]
        total_valid += qa["valid_count"]
        total_expected += qa["total_count"]
        total_flags += len(qa["flags"])
        all_quality_scores.append(qa["quality_score"])

    overall_valid_rate = round((total_valid / total_expected) * 100, 2) if total_expected else 0.0
    avg_quality_score = round(np.mean(all_quality_scores), 1) if all_quality_scores else 0.0

    summary = {
        "stations": len(processed),
        "overall_valid_rate_pct": overall_valid_rate,
        "avg_quality_score": avg_quality_score,
        "total_flags": total_flags,
        "method": "SaQC_framework",
        "scientific_basis": [
            "Schmidt et al. (2023) - System for automated Quality Control (SaQC)",
            "Faybishenko et al. (2022) - QA/QC of meteorological time series data",
            "D'Amore et al. (2015) - Data quality through a web-based QA/QC system",
        ],
    }
    return processed, summary
