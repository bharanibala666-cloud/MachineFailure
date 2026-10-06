from flask import Flask, render_template, request
import logging
import json
import os

from services.prediction_service import PredictionService
from services.validation_service import ValidationService

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


@app.route("/", methods=["GET", "POST"])
def home():
    """Main route for prediction interface"""
    
    # Default values
    result = None
    probability = None
    error = None
    
    air_temperature = None
    process_temperature = None
    rotational_speed = None
    torque = None
    tool_wear = None
    machine_type = None

    if request.method == "POST":
        try:
            # Check if model is loaded
            if not prediction_service.is_model_loaded():
                error = "Prediction model is not available. Please contact support."
                logger.error("Model not loaded - cannot make prediction")
                return render_template("index.html", error=error, config=model_config)

            # Get form data
            machine_type = request.form.get("machine_type", "").upper()
            
            # Get numeric inputs with error handling
            try:
                air_temperature = float(request.form.get("air_temperature", 0))
                process_temperature = float(request.form.get("process_temperature", 0))
                rotational_speed = float(request.form.get("rotational_speed", 0))
                torque = float(request.form.get("torque", 0))
                tool_wear = float(request.form.get("tool_wear", 0))
            except ValueError as e:
                error = "All input fields must contain valid numbers"
                logger.warning(f"Invalid numeric input: {str(e)}")
                return render_template(
                    "index.html",
                    error=error,
                    machine_type=machine_type,
                    config=model_config
                )

            # Validate all inputs using validation service
            is_valid, validation_errors = validation_service.validate_all_inputs(
                machine_type=machine_type,
                air_temperature=air_temperature,
                process_temperature=process_temperature,
                rotational_speed=rotational_speed,
                torque=torque,
                tool_wear=tool_wear
            )
            
            if not is_valid:
                error = " | ".join(validation_errors)
                logger.warning(f"Validation errors: {error}")
                return render_template(
                    "index.html",
                    error=error,
                    air_temperature=air_temperature,
                    process_temperature=process_temperature,
                    rotational_speed=rotational_speed,
                    torque=torque,
                    tool_wear=tool_wear,
                    machine_type=machine_type,
                    config=model_config
                )

            # Make prediction using prediction service
            try:
                result, probability = prediction_service.predict(
                    machine_type=machine_type,
                    air_temperature=air_temperature,
                    process_temperature=process_temperature,
                    rotational_speed=rotational_speed,
                    torque=torque,
                    tool_wear=tool_wear
                )
                
                logger.info(f"Prediction successful: {result} ({probability:.2f}%)")
                
            except RuntimeError as e:
                error = str(e)
                logger.error(f"Runtime error during prediction: {str(e)}")
            except Exception as e:
                error = "An error occurred during prediction. Please try again."
                logger.error(f"Prediction error: {str(e)}")

        except Exception as e:
            error = "An unexpected error occurred. Please try again."
            logger.error(f"Unexpected error in home route: {str(e)}")

    return render_template(
        "index.html",
        result=result,
        probability=probability,
        error=error,
        air_temperature=air_temperature,
        process_temperature=process_temperature,
        rotational_speed=rotational_speed,
        torque=torque,
        tool_wear=tool_wear,
        machine_type=machine_type,
        config=model_config
    )


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template("index.html", error="Page not found", config=model_config), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}")
    return render_template("index.html", error="Internal server error. Please try again.", config=model_config), 500


if __name__ == "__main__":
    # Check model status on startup
    if prediction_service.is_model_loaded():
        logger.info("Application starting with model loaded successfully")
    else:
        logger.warning("Application starting but model failed to load")
    
    app.run(debug=True, port=5001)
