import pandas as pd
import joblib
import os


# Get the project root directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load the trained model
model_path = os.path.join(
    BASE_DIR,
    "models",
    "predictive_maintenance_xgboost.pkl"
)

model = joblib.load(model_path)


def predict_machine_failure(
    machine_type,
    air_temperature,
    process_temperature,
    rotational_speed,
    torque,
    tool_wear
):
    # Create input data
    input_data = pd.DataFrame({
        "Type": [machine_type],
        "Air temperature [K]": [air_temperature],
        "Process temperature [K]": [process_temperature],
        "Rotational speed [rpm]": [rotational_speed],
        "Torque [Nm]": [torque],
        "Tool wear [min]": [tool_wear]
    })

    # Prediction
    prediction = model.predict(input_data)[0]

    # Failure probability
    probability = model.predict_proba(input_data)[0][1]

    if prediction == 1:
        result = "Machine Failure"
    else:
        result = "No Machine Failure"

    print("\n===== Prediction Result =====")
    print("Prediction:", result)
    print("Failure Probability:", round(probability * 100, 2), "%")


# User input
print("===== Predictive Maintenance System =====")

machine_type = input("Enter machine type (L/M/H): ").upper()
air_temperature = float(input("Enter air temperature [K]: "))
process_temperature = float(input("Enter process temperature [K]: "))
rotational_speed = float(input("Enter rotational speed [rpm]: "))
torque = float(input("Enter torque [Nm]: "))
tool_wear = float(input("Enter tool wear [min]: "))

predict_machine_failure(
    machine_type,
    air_temperature,
    process_temperature,
    rotational_speed,
    torque,
    tool_wear
)