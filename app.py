from flask import Flask, render_template, request
import logging
import json
import os

from services.prediction_service import PredictionService
from services.validation_service import ValidationService
from services.feature_engineering import explain_failure_modes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Project folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Initialize services
prediction_service = PredictionService()
validation_service = ValidationService()

# Load model configuration
config_path = os.path.join(BASE_DIR, 'config', 'model_config.json')
model_config = {}

try:
    with open(config_path, 'r') as f:
        model_config = json.load(f)
    logger.info("Model configuration loaded successfully")
except FileNotFoundError:
    logger.warning(f"Configuration file not found at {config_path}")
except Exception as e:
    logger.error(f"Error loading configuration: {str(e)}")


NUMERIC_FIELDS = [
    "air_temperature",
    "process_temperature",
    "rotational_speed",
    "torque",
    "tool_wear",
]


@app.context_processor
def inject_globals():
    """Values every page render needs, including error pages (routes can override)"""
    return {
        "form_values": {},
        "values": {},
        "config": model_config,
        "model_ready": prediction_service.is_model_loaded(),
        "sensor_ranges": validation_service.get_validation_rules(),
    }


@app.route("/", methods=["GET", "POST"])
def home():
    """Main route for prediction interface"""
    
    result = None
    probability = None
    failure_modes = None
    error = None
    
    # Raw text the user typed, re-displayed in the form after any error
    form_values = {}
    # Parsed numbers, only set once all inputs are valid
    values = {}

    if request.method == "POST":
        form_values = {
            field: request.form.get(field, "").strip()
            for field in ["machine_type"] + NUMERIC_FIELDS
        }
        form_values["machine_type"] = form_values["machine_type"].upper()

        try:
            if not prediction_service.is_model_loaded():
                error = "Prediction model is not available. Please contact support."
                logger.error("Model not loaded - cannot make prediction")
            else:
                is_valid, validation_errors = validation_service.validate_all_inputs(**form_values)

                if not is_valid:
                    error = " | ".join(validation_errors)
                    logger.warning(f"Validation errors: {error}")
                else:
                    values = {field: float(form_values[field]) for field in NUMERIC_FIELDS}
                    machine_type = form_values["machine_type"]

                    result, probability = prediction_service.predict(machine_type=machine_type, **values)
                    logger.info(f"Prediction successful: {result} ({probability:.2f}%)")

                    # Explain which physical failure mechanisms are at risk
                    failure_modes = explain_failure_modes(machine_type=machine_type, **values)

        except Exception as e:
            result = None
            error = "An error occurred during prediction. Please try again."
            logger.error(f"Prediction error: {str(e)}")

    return render_template(
        "index.html",
        result=result,
        probability=probability,
        failure_modes=failure_modes,
        error=error,
        form_values=form_values,
        values=values if result else {},
    )


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template("index.html", error="Page not found"), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}")
    return render_template("index.html", error="Internal server error. Please try again."), 500


if __name__ == "__main__":
    # Check model status on startup
    if prediction_service.is_model_loaded():
        logger.info("Application starting with model loaded successfully")
    else:
        logger.warning("Application starting but model failed to load")
    
    app.run(debug=True, port=5001)
