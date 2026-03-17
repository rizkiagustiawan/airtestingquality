from copy import deepcopy


RANGE_RULES = {
    "pm25": (0.0, 500.0),
    "pm10": (0.0, 600.0),
    "so2": (0.0, 1200.0),
    "no2": (0.0, 3000.0),
    "co": (0.0, 50000.0),
    "o3": (0.0, 1000.0),
}


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float))


def run_qaqc_on_station(station: dict, prev_measurements: dict | None = None) -> dict:
    """
    Applies baseline QA/QC checks and returns station with:
    - measurements_raw
    - measurements (cleaned)
    - qa_qc summary
    """
    prev = prev_measurements or {}
    raw = deepcopy(station.get("measurements", {}))
    cleaned = {}
    flags = []

    for pollutant, (min_val, max_val) in RANGE_RULES.items():
        value = raw.get(pollutant)
        if value is None:
            flags.append({"pollutant": pollutant, "code": "missing", "detail": "No value in input payload"})
            continue
        if not _is_number(value):
            flags.append({"pollutant": pollutant, "code": "non_numeric", "detail": "Value is not numeric"})
            continue
        if float(value) < min_val or float(value) > max_val:
            flags.append(
                {
                    "pollutant": pollutant,
                    "code": "out_of_range",
                    "detail": f"Expected between {min_val} and {max_val}",
                }
            )
            continue

        previous = prev.get(pollutant)
        if _is_number(previous):
            baseline = max(abs(float(previous)), 1.0)
            jump_ratio = abs(float(value) - float(previous)) / baseline
            if jump_ratio > 3.0:
                flags.append(
                    {
                        "pollutant": pollutant,
                        "code": "spike_suspect",
                        "detail": "Abrupt jump >300% from previous value",
                    }
                )

        cleaned[pollutant] = float(value)

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
        "flags": flags,
    }
    return out


def run_qaqc(
    stations: list[dict], previous_by_station: dict[str, dict] | None = None
) -> tuple[list[dict], dict]:
    processed = []
    total_valid = 0
    total_expected = 0
    total_flags = 0
    prev_map = previous_by_station or {}

    for station in stations:
        station_id = str(station.get("id", ""))
        checked = run_qaqc_on_station(station, prev_measurements=prev_map.get(station_id))
        processed.append(checked)
        qa = checked["qa_qc"]
        total_valid += qa["valid_count"]
        total_expected += qa["total_count"]
        total_flags += len(qa["flags"])

    overall_valid_rate = round((total_valid / total_expected) * 100, 2) if total_expected else 0.0
    summary = {
        "stations": len(processed),
        "overall_valid_rate_pct": overall_valid_rate,
        "total_flags": total_flags,
    }
    return processed, summary
