"""
Physics-Informed Feature Engineering

Instead of feeding raw sensor readings to the model and hoping it discovers
the physics on its own, we compute the three quantities that actually drive
machine failure in the AI4I 2020 dataset:

    Power  [W]      = Torque x Angular velocity   -> Power failure (PWF)
    Temp diff [K]   = Process temp - Air temp      -> Heat dissipation failure (HDF)
    Strain [min*Nm] = Tool wear x Torque           -> Overstrain failure (OSF)

The same functions are used for training and for live predictions, so the
model always sees identical features.
"""
import math

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder

# Raw inputs the user provides (unchanged from the original model)
RAW_FEATURES = [
    "Type",
    "Air temperature [K]",
    "Process temperature [K]",
    "Rotational speed [rpm]",
    "Torque [Nm]",
    "Tool wear [min]",
]

# Engineered features (names avoid [ ] < because XGBoost rejects them)
POWER = "Power (W)"
TEMP_DIFF = "Temp diff (K)"
STRAIN = "Strain (min*Nm)"

# Columns the model is trained on after feature engineering
PHYSICS_NUMERIC_FEATURES = [
    POWER,
    TEMP_DIFF,
    STRAIN,
    "Tool wear [min]",
    "Rotational speed [rpm]",
]

# Documented failure limits of the AI4I 2020 dataset (Matzka, 2020)
POWER_MIN_W = 3500
POWER_MAX_W = 9000
HEAT_TEMP_DIFF_MIN_K = 8.6
HEAT_RPM_MAX = 1380
STRAIN_LIMITS = {"L": 11000, "M": 12000, "H": 13000}
TOOL_WEAR_RISK_MIN = 200

# How close to a limit (as a fraction) counts as a "warning"
WARNING_MARGIN = 0.10


def compute_power(torque, rotational_speed):
    """Mechanical power in watts: P = T x w, with w = rpm x 2pi / 60."""
    return torque * rotational_speed * 2 * math.pi / 60


def add_physics_features(df):
    """Return a copy of df with Power, Temp diff and Strain columns added."""
    df = df.copy()
    df[POWER] = compute_power(df["Torque [Nm]"], df["Rotational speed [rpm]"])
    df[TEMP_DIFF] = df["Process temperature [K]"] - df["Air temperature [K]"]
    df[STRAIN] = df["Tool wear [min]"] * df["Torque [Nm]"]
    return df


def build_physics_pipeline(classifier):
    """
    Pipeline: raw inputs -> physics features -> one-hot Type -> classifier.

    Tree models do not need scaling, so numeric features pass straight through.
    """
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", "passthrough", PHYSICS_NUMERIC_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore"), ["Type"]),
        ]
    )
    return Pipeline([
        ("physics", FunctionTransformer(add_physics_features)),
        ("preprocessor", preprocessor),
        ("classifier", classifier),
    ])


def _status(is_risk, is_warning):
    if is_risk:
        return "risk"
    if is_warning:
        return "warning"
    return "ok"


def explain_failure_modes(machine_type, air_temperature, process_temperature,
                          rotational_speed, torque, tool_wear):
    """
    Check each physical failure mode against its documented limit.

    Returns:
        list of dicts with keys: code, name, value, limit, status, message
        status is one of "risk", "warning", "ok"
    """
    machine_type = machine_type.upper()
    power = compute_power(torque, rotational_speed)
    temp_diff = process_temperature - air_temperature
    strain = tool_wear * torque
    strain_limit = STRAIN_LIMITS.get(machine_type, STRAIN_LIMITS["L"])

    checks = []

    # Power failure: power outside the 3500-9000 W band
    power_low = power < POWER_MIN_W
    power_high = power > POWER_MAX_W
    power_near = (power < POWER_MIN_W * (1 + WARNING_MARGIN)
                  or power > POWER_MAX_W * (1 - WARNING_MARGIN))
    if power_low:
        power_msg = f"Power {power:,.0f} W is below the {POWER_MIN_W:,} W minimum"
    elif power_high:
        power_msg = f"Power {power:,.0f} W is above the {POWER_MAX_W:,} W maximum"
    elif power_near:
        power_msg = f"Power {power:,.0f} W is close to the {POWER_MIN_W:,}-{POWER_MAX_W:,} W safe band edge"
    else:
        power_msg = f"Power {power:,.0f} W is within the safe band"
    checks.append({
        "code": "PWF",
        "name": "Power Failure",
        "value": f"{power:,.0f} W",
        "limit": f"{POWER_MIN_W:,}-{POWER_MAX_W:,} W",
        "status": _status(power_low or power_high, power_near),
        "message": power_msg,
    })

    # Heat dissipation failure: small temp gap AND low speed
    heat_risk = temp_diff < HEAT_TEMP_DIFF_MIN_K and rotational_speed < HEAT_RPM_MAX
    heat_near = (temp_diff < HEAT_TEMP_DIFF_MIN_K * (1 + WARNING_MARGIN)
                 and rotational_speed < HEAT_RPM_MAX * (1 + WARNING_MARGIN))
    if heat_risk:
        heat_msg = (f"Temp gap {temp_diff:.1f} K < {HEAT_TEMP_DIFF_MIN_K} K at only "
                    f"{rotational_speed:.0f} rpm — heat cannot dissipate")
    elif heat_near:
        heat_msg = f"Temp gap {temp_diff:.1f} K at {rotational_speed:.0f} rpm is close to the cooling limit"
    else:
        heat_msg = f"Temp gap {temp_diff:.1f} K gives enough cooling"
    checks.append({
        "code": "HDF",
        "name": "Heat Dissipation",
        "value": f"{temp_diff:.1f} K @ {rotational_speed:.0f} rpm",
        "limit": f"≥ {HEAT_TEMP_DIFF_MIN_K} K or ≥ {HEAT_RPM_MAX} rpm",
        "status": _status(heat_risk, heat_near),
        "message": heat_msg,
    })

    # Overstrain failure: tool wear x torque above the per-type limit
    strain_risk = strain > strain_limit
    strain_near = strain > strain_limit * (1 - WARNING_MARGIN)
    if strain_risk:
        strain_msg = f"Strain {strain:,.0f} exceeds the type-{machine_type} limit of {strain_limit:,}"
    elif strain_near:
        strain_msg = f"Strain {strain:,.0f} is close to the type-{machine_type} limit of {strain_limit:,}"
    else:
        strain_msg = f"Strain {strain:,.0f} is well below the type-{machine_type} limit"
    checks.append({
        "code": "OSF",
        "name": "Overstrain",
        "value": f"{strain:,.0f} min·Nm",
        "limit": f"≤ {strain_limit:,} min·Nm",
        "status": _status(strain_risk, strain_near),
        "message": strain_msg,
    })

    # Tool wear failure: random replacement between 200-240 min (not fully predictable)
    wear_risk = tool_wear >= TOOL_WEAR_RISK_MIN
    wear_near = tool_wear >= TOOL_WEAR_RISK_MIN * (1 - WARNING_MARGIN)
    if wear_risk:
        wear_msg = f"Tool wear {tool_wear:.0f} min is in the 200-240 min failure window — replace tool"
    elif wear_near:
        wear_msg = f"Tool wear {tool_wear:.0f} min is approaching the 200 min failure window"
    else:
        wear_msg = f"Tool wear {tool_wear:.0f} min is below the failure window"
    checks.append({
        "code": "TWF",
        "name": "Tool Wear",
        "value": f"{tool_wear:.0f} min",
        "limit": f"< {TOOL_WEAR_RISK_MIN} min",
        "status": _status(wear_risk, wear_near),
        "message": wear_msg,
    })

    return checks


def to_input_frame(machine_type, air_temperature, process_temperature,
                   rotational_speed, torque, tool_wear):
    """Build the single-row raw input DataFrame the pipeline expects."""
    return pd.DataFrame({
        "Type": [machine_type],
        "Air temperature [K]": [air_temperature],
        "Process temperature [K]": [process_temperature],
        "Rotational speed [rpm]": [rotational_speed],
        "Torque [Nm]": [torque],
        "Tool wear [min]": [tool_wear],
    })
