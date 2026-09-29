from flask import Flask, render_template, request
import pandas as pd
import joblib
import os

app = Flask(__name__)

# Project folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load trained model
model_path = os.path.join(
    BASE_DIR,
    "models",
    "predictive_maintenance_xgboost.pkl"
)

model = joblib.load(model_path)


@app.route("/", methods=["GET", "POST"])
def home():

    # Default values for first page load
    result = None
    probability = None

    air_temperature = None
    process_temperature = None
    rotational_speed = None
    torque = None
    tool_wear = None

    if request.method == "POST":

        machine_type = request.form["machine_type"]

        air_temperature = float(request.form["air_temperature"])
        process_temperature = float(request.form["process_temperature"])
        rotational_speed = float(request.form["rotational_speed"])
        torque = float(request.form["torque"])
        tool_wear = float(request.form["tool_wear"])

        # Create input dataframe
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

        probability = model.predict_proba(input_data)[0][1] * 100

        if prediction == 1:
            result = "Machine Failure"
        else:
            result = "No Machine Failure"

    return render_template(
        "index.html",
        result=result,
        probability=probability,
        air_temperature=air_temperature,
        process_temperature=process_temperature,
        rotational_speed=rotational_speed,
        torque=torque,
        tool_wear=tool_wear
    )


if __name__ == "__main__":
    app.run(debug=True)