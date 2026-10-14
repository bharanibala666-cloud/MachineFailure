"""
Prediction Service - Handles model loading and predictions
"""
import joblib
import json
import os
import logging

from services.feature_engineering import to_input_frame

logger = logging.getLogger(__name__)


class PredictionService:
    """Service for handling machine failure predictions"""
    
    _instance = None
    _model = None
    _model_loaded = False
    _threshold = 0.5
    
    def __new__(cls):
        """Singleton pattern to ensure model is loaded only once"""
        if cls._instance is None:
            cls._instance = super(PredictionService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the prediction service"""
        if not self._model_loaded:
            self._load_model()
    
    def _load_model(self):
        """Load the trained model from disk"""
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            model_path = os.path.join(base_dir, "models", "predictive_maintenance_xgboost_physics.pkl")
            
            self._model = joblib.load(model_path)
            self._model_loaded = True
            logger.info(f"Model loaded successfully from {model_path}")
            
            # Decision threshold tuned by cross-validation in train_model.py
            config_path = os.path.join(base_dir, "config", "model_config.json")
            try:
                with open(config_path) as f:
                    self._threshold = json.load(f)["model"]["threshold"]
            except (FileNotFoundError, KeyError):
                logger.warning("No threshold in config, using 0.5")
            logger.info(f"Decision threshold: {self._threshold}")
            
        except FileNotFoundError:
            logger.error(f"Model file not found at {model_path}")
            self._model_loaded = False
            raise
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            self._model_loaded = False
            raise
    
    def is_model_loaded(self):
        """Check if model is loaded and ready"""
        return self._model_loaded and self._model is not None
    
    def predict(self, machine_type, air_temperature, process_temperature, 
                rotational_speed, torque, tool_wear):
        """
        Make a prediction for machine failure
        
        Args:
            machine_type (str): Type of machine (L, M, or H)
            air_temperature (float): Air temperature in Kelvin
            process_temperature (float): Process temperature in Kelvin
            rotational_speed (float): Rotational speed in RPM
            torque (float): Torque in Nm
            tool_wear (float): Tool wear in minutes
            
        Returns:
            tuple: (result_string, probability_percentage)
            
        Raises:
            RuntimeError: If model is not loaded
            Exception: If prediction fails
        """
        if not self.is_model_loaded():
            raise RuntimeError("Prediction model is not loaded")
        
        try:
            # Raw inputs; the pipeline computes the physics features itself
            input_data = to_input_frame(machine_type, air_temperature, process_temperature,
                                        rotational_speed, torque, tool_wear)
            
            failure_proba = self._model.predict_proba(input_data)[0][1]
            probability = failure_proba * 100
            
            # Convert prediction to human-readable result
            if failure_proba >= self._threshold:
                result = "Machine Failure"
            else:
                result = "No Machine Failure"
            
            logger.info(f"Prediction: {result} (probability: {probability:.2f}%)")
            
            return result, probability
            
        except Exception as e:
            logger.error(f"Prediction error: {str(e)}")
            raise
