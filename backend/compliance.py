def get_compliance_limits():
    """
    Returns the maximum limits based on Indonesian PP 22/2021 and WHO 2021 guidelines.
    Values are in ug/m3.
    """
    return {
        "pm25": {
            "pp22_24h": 55,
            "who_24h": 15
        },
        "pm10": {
            "pp22_24h": 75,
            "who_24h": 45
        },
        "so2": {
            "pp22_24h": 75,
            "who_24h": 40,
            "pp22_1h": 150
        },
        "no2": {
            "pp22_24h": 65,
            "who_24h": 25,
            "pp22_1h": 200
        },
        "co": {
             "pp22_1h": 30000,
             "pp22_8h": 10000
        },
        "o3": {
             "pp22_1h": 150,
             "who_8h": 100
        }
    }

def verify_compliance(parameter: str, concentration: float, timeframe="24h") -> dict:
    limits = get_compliance_limits()
    param = parameter.lower().replace('.', '')
    
    if param not in limits:
        return {"status": "unknown"}
        
    param_limits = limits[param]
    result = {"parameter": parameter, "concentration": concentration, "timeframe": timeframe}
    
    # Check Indonesia PP 22/2021
    indo_key = f"pp22_{timeframe}"
    if indo_key in param_limits:
        limit_val = param_limits[indo_key]
        result["indonesia_compliant"] = concentration <= limit_val
        result["indonesia_limit"] = limit_val
    else:
        result["indonesia_compliant"] = None
        result["indonesia_note"] = f"No PP22 {timeframe} limit configured"
            
    # Check WHO 2021 Guidelines
    who_key = f"who_{timeframe}"
    if who_key in param_limits:
        limit_val = param_limits[who_key]
        result["who_compliant"] = concentration <= limit_val
        result["who_limit"] = limit_val
    else:
        result["who_compliant"] = None
        result["who_note"] = f"No WHO {timeframe} limit configured"
            
    return result
