def get_ispu_breakpoints():
    # Breakpoint tables based on PermenLHK No. 14 Tahun 2020
    # Values represent [ISPU Low, ISPU High, Conc Low, Conc High]
    return {
        "pm25": [
            [0, 50, 0, 15.5],
            [51, 100, 15.6, 55.4],
            [101, 200, 55.5, 150.4],
            [201, 300, 150.5, 250.4],
            [301, 500, 250.5, 500.0]  # Above 500 is clamped
        ],
        "pm10": [
            [0, 50, 0, 50],
            [51, 100, 51, 150],
            [101, 200, 151, 350],
            [201, 300, 351, 420],
            [301, 500, 421, 600]
        ],
        "so2": [ # 24 hour (ug/m3) => but usually ISPU uses 24h
            [0, 50, 0, 52],
            [51, 100, 53, 180],
            [101, 200, 181, 400],
            [201, 300, 401, 800],
            [301, 500, 801, 1200]
        ],
        "no2": [ # 1 hour mapping
            [0, 50, 0, 80],
            [51, 100, 81, 200],
            [101, 200, 201, 1130],
            [201, 300, 1131, 2260],
            [301, 500, 2261, 3000]
        ],
        "o3": [ # 1 hour mapping
            [0, 50, 0, 120],
            [51, 100, 121, 235],
            [101, 200, 236, 400],
            [201, 300, 401, 800],
            [301, 500, 801, 1000]
        ],
        "co": [ # 8 hour mapping
            [0, 50, 0, 4000],
            [51, 100, 4001, 8000],
            [101, 200, 8001, 15000],
            [201, 300, 15001, 30000],
            [301, 500, 30001, 45000]
        ]
    }

def calculate_ispu(parameter: str, concentration: float) -> dict:
    breakpoints_table = get_ispu_breakpoints()
    
    # Normalize parameter name
    param = parameter.lower().replace('.', '')
    
    if param not in breakpoints_table:
        return {"value": None, "category": "N/A", "color": "gray"}
        
    breakpoints = breakpoints_table[param]
    
    # Check bounds
    highest_bp = breakpoints[-1]
    if concentration > highest_bp[3]:
        return {"value": highest_bp[1], "category": "Berbahaya", "color": "#000000"}  # Black
        
    for bp in breakpoints:
        ispu_lo, ispu_hi, conc_lo, conc_hi = bp
        if conc_lo <= concentration <= conc_hi:
            # ISPU formula: I = ((I_a - I_b)/(X_a - X_b)) * (X_x - X_b) + I_b
            ispu_val = ((ispu_hi - ispu_lo) / (conc_hi - conc_lo)) * (concentration - conc_lo) + ispu_lo
            ispu_rounded = round(ispu_val)
            category, color = get_ispu_category_and_color(ispu_rounded)
            return {"value": ispu_rounded, "category": category, "color": color}
            
    # Fallback
    return {"value": 0, "category": "Baik", "color": "#00e400"}
    
def get_ispu_category_and_color(ispu: int) -> tuple:
    if ispu <= 50:
        return ("Baik", "#00e400")  # Green
    if ispu <= 100:
        return ("Sedang", "#0080ff")  # Blue
    if ispu <= 200:
        return ("Tidak Sehat", "#ffff00")  # Yellow
    if ispu <= 300:
        return ("Sangat Tidak Sehat", "#ff0000")  # Red
    return ("Berbahaya", "#000000")  # Black

def get_overall_ispu(metrics: dict) -> dict:
    """Takes a dictionary of parameters and concentrations and returns the overall ISPU (highest)"""
    highest_ispu = -1
    highest_parameter = None
    result_category = "Baik"
    result_color = "#00e400"
    
    for param, conc in metrics.items():
        if conc is not None:
            res = calculate_ispu(param, conc)
            if res["value"] is not None and res["value"] > highest_ispu:
                highest_ispu = res["value"]
                highest_parameter = param
                result_category = res["category"]
                result_color = res["color"]
                
    if highest_ispu == -1:
        return {"value": 0, "category": "N/A", "color": "gray", "critical_parameter": None}
         
    return {
        "value": highest_ispu, 
        "category": result_category, 
        "color": result_color, 
        "critical_parameter": highest_parameter
    }
