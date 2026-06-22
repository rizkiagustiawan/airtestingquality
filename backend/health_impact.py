"""
Health Impact Assessment (HIA) Module: AirQ+ Methodology.

Scientific basis:
- Conti et al. (2017) "A review of AirQ Models and their applications" - 164 citations
- Liu et al. (2019) "Ambient Particulate Air Pollution and Daily Mortality in 652 Cities" - 1,667 citations
- Chen et al. (2020) "Long-term exposure to PM and all-cause mortality" - 1,021 citations
- WHO (2021) Global Air Quality Guidelines
- Orellano et al. (2020) "Short-term exposure to PM10, PM2.5, NO2, O3" - 777 citations

Implements WHO AirQ+ methodology for health impact estimation:
- Attributable Proportion (AP) calculation
- Concentration-Response Functions (CRR) from epidemiological studies
- Excess mortality and morbidity risk estimation
- Hazard Quotient (HQ) for non-carcinogenic risk
"""

import math

# WHO 2021 Air Quality Guidelines (µg/m³)
WHO_GUIDELINES = {
    "pm25": {"annual": 5, "24h": 15},
    "pm10": {"annual": 15, "24h": 45},
    "no2": {"annual": 10, "24h": 25},
    "o3": {"8h": 100},
    "so2": {"24h": 40},
}

# Indonesian PP 22/2021 Ambient Standards (µg/m³)
PP22_LIMITS = {
    "pm25": {"24h": 55},
    "pm10": {"24h": 75},
    "so2": {"24h": 75, "1h": 150},
    "no2": {"24h": 65, "1h": 200},
    "co": {"8h": 10000, "1h": 30000},
    "o3": {"1h": 150, "8h": 100},
}

# Concentration-Response Functions (CRR) per 10 µg/m³ increase
# Sources: WHO AirQ+ guidelines, Liu et al. 2019, Chen et al. 2020, Orellano et al. 2020
CRR_COEFFICIENTS = {
    "pm25": {
        "mortality_all_causes": 1.06,  # 6% increase per 10 µg/m³ (Chen et al. 2020)
        "mortality_respiratory": 1.14,  # 14% increase (Liu et al. 2019)
        "mortality_cardiovascular": 1.11,  # 11% increase (Liu et al. 2019)
        "morbidity_respiratory": 1.08,  # 8% increase
        "morbidity_cardiovascular": 1.05,  # 5% increase
    },
    "pm10": {
        "mortality_all_causes": 1.04,  # 4% increase per 10 µg/m³
        "mortality_respiratory": 1.08,
        "mortality_cardiovascular": 1.06,
        "morbidity_respiratory": 1.05,
        "morbidity_cardiovascular": 1.03,
    },
    "no2": {
        "mortality_all_causes": 1.02,  # 2% increase per 10 µg/m³
        "mortality_respiratory": 1.05,
        "morbidity_respiratory": 1.03,
    },
    "o3": {
        "mortality_all_causes": 1.03,  # 3% increase per 10 ppb (~2 µg/m³)
        "mortality_respiratory": 1.07,
        "morbidity_respiratory": 1.04,
    },
    "so2": {
        "mortality_all_causes": 1.02,
        "morbidity_respiratory": 1.04,
    },
}

# Reference concentration for CRR (counterfactual/minimum threshold)
# Per WHO methodology: minimum concentration below which no adverse effects
COUNTERFACTUAL = {
    "pm25": 5.0,  # WHO annual guideline
    "pm10": 15.0,  # WHO annual guideline
    "no2": 10.0,  # WHO annual guideline
    "o3": 70.0,  # ~WHO equivalent
    "so2": 20.0,  # Conservative threshold
}

# Reference dose for Hazard Quotient (mg/m³)
RFD = {
    "pm25": 0.015,  # µg/m³ -> mg/m³
    "pm10": 0.045,
    "no2": 0.04,
    "o3": 0.07,
    "so2": 0.02,
}


def _attributable_proportion(concentration: float, crr: float, counterfactual: float) -> float:
    """
    Calculate Attributable Proportion (AP) using WHO AirQ+ methodology.

    AP = 1 - exp(-β × (C - C₀))
    Where:
        β = ln(CRR) / 10  (CRR per 10 µg/m³)
        C = measured concentration
        C₀ = counterfactual (minimum threshold)

    Reference: Conti et al. (2017), WHO AirQ+ technical documentation
    """
    if concentration <= counterfactual:
        return 0.0

    beta = math.log(crr) / 10.0
    ap = 1 - math.exp(-beta * (concentration - counterfactual))
    return max(0.0, min(1.0, ap))


def _hazard_quotient(concentration: float, rfd: float) -> float:
    """
    Calculate Hazard Quotient (HQ) for non-carcinogenic risk.

    HQ = Exposure Concentration / Reference Dose
    HQ > 1 indicates potential health concern.

    Standard toxicological risk assessment methodology.
    """
    conc_mg = concentration / 1000.0  # µg/m³ to mg/m³
    if rfd <= 0:
        return 0.0
    return conc_mg / rfd


def assess_health_impact(measurements: dict, population: int = 100000) -> dict:
    """
    Comprehensive health impact assessment using WHO AirQ+ methodology.

    Calculates:
    - Attributable Proportion (AP) for each pollutant and health endpoint
    - Hazard Quotient (HQ) for non-carcinogenic risk
    - Excess cases estimation (requires population)
    - Overall risk level

    Based on:
    - Conti et al. (2017) AirQ model review
    - WHO (2021) Air Quality Guidelines
    - Liu et al. (2019) PM2.5 mortality study
    """
    results = {}
    overall_risk_score = 0.0

    for pollutant in ["pm25", "pm10", "no2", "o3", "so2"]:
        conc = measurements.get(pollutant)
        if conc is None:
            continue

        conc = float(conc)
        crr_data = CRR_COEFFICIENTS.get(pollutant, {})
        counterfactual = COUNTERFACTUAL.get(pollutant, 0)
        rfd = RFD.get(pollutant, 0.01)

        # AP for each health endpoint
        ap_results = {}
        for endpoint, crr in crr_data.items():
            ap = _attributable_proportion(conc, crr, counterfactual)
            # Estimated excess cases per 100,000 population
            baseline_rate = _get_baseline_rate(endpoint)
            excess_cases = ap * baseline_rate * population / 100000
            ap_results[endpoint] = {
                "ap_pct": round(ap * 100, 2),
                "crr_per_10ug": crr,
                "excess_cases_per_100k": round(excess_cases, 1),
            }

        # Hazard Quotient
        hq = _hazard_quotient(conc, rfd)

        # Compliance check
        who_limit = WHO_GUIDELINES.get(pollutant, {}).get("24h")
        pp22_limit = PP22_LIMITS.get(pollutant, {}).get("24h")

        results[pollutant] = {
            "concentration": conc,
            "unit": "µg/m³",
            "who_guideline": who_limit,
            "pp22_limit": pp22_limit,
            "exceeds_who": conc > who_limit if who_limit else None,
            "exceeds_pp22": conc > pp22_limit if pp22_limit else None,
            "attributable_proportions": ap_results,
            "hazard_quotient": round(hq, 3),
            "hq_exceeds_threshold": hq > 1.0,
        }

        # Accumulate risk score
        max_ap = max((v["ap_pct"] for v in ap_results.values()), default=0)
        overall_risk_score += max_ap + (hq * 10 if hq > 1 else 0)

    # Overall risk level
    if overall_risk_score > 50:
        risk_level = "high"
    elif overall_risk_score > 20:
        risk_level = "moderate"
    else:
        risk_level = "low"

    return {
        "status": "success",
        "population_reference": population,
        "risk_level": risk_level,
        "overall_risk_score": round(overall_risk_score, 1),
        "pollutant_impacts": results,
        "method": "WHO_AirQ_plus",
        "scientific_basis": [
            "Conti et al. (2017) - A review of AirQ Models and their applications - 164 citations",
            "Liu et al. (2019) - Ambient Particulate Air Pollution and Daily Mortality - 1,667 citations",
            "Chen et al. (2020) - Long-term exposure to PM and mortality - 1,021 citations",
            "Orellano et al. (2020) - Short-term exposure to PM10, PM2.5, NO2, O3 - 777 citations",
            "WHO (2021) - Global Air Quality Guidelines",
        ],
        "notes": [
            "AP calculated using concentration-response functions from peer-reviewed meta-analyses",
            "Excess cases are estimates based on population attributable fraction",
            "Counterfactual concentrations based on WHO 2021 guidelines",
            "Results are screening-level indicators, not substitutes for formal health assessments",
        ],
    }


def _get_baseline_rate(endpoint: str) -> float:
    """
    Baseline incidence rates per 100,000 population (approximate for Indonesia).

    Sources: WHO Global Health Observatory, Indonesian Basic Health Survey (Riskesdas).
    """
    rates = {
        "mortality_all_causes": 700.0,
        "mortality_respiratory": 60.0,
        "mortality_cardiovascular": 200.0,
        "morbidity_respiratory": 15000.0,
        "morbidity_cardiovascular": 3000.0,
    }
    return rates.get(endpoint, 500.0)


def get_risk_summary(measurements: dict) -> dict:
    """Quick risk summary for dashboard display."""
    impact = assess_health_impact(measurements)

    alerts = []
    for p, data in impact.get("pollutant_impacts", {}).items():
        if data.get("exceeds_who"):
            alerts.append(
                {
                    "pollutant": p,
                    "severity": "warning",
                    "message": f"{p.upper()} ({data['concentration']} µg/m³) exceeds WHO guideline ({data['who_guideline']} µg/m³)",
                }
            )
        if data.get("hq_exceeds_threshold"):
            alerts.append(
                {
                    "pollutant": p,
                    "severity": "critical",
                    "message": f"{p.upper()} Hazard Quotient ({data['hazard_quotient']}) exceeds safe threshold (1.0)",
                }
            )

    return {
        "risk_level": impact["risk_level"],
        "risk_score": impact["overall_risk_score"],
        "alerts": alerts,
        "exceeds_who_count": sum(
            1 for d in impact["pollutant_impacts"].values() if d.get("exceeds_who")
        ),
    }
