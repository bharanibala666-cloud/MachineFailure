"""
Prediction Service - Handles model loading and predictions
"""
import pandas as pd
import joblib
import os
import logging

logger = logging.getLogger(__name__)


class PredictionService:
    """Service for handling machine failure predictions"""
    
    _instance = None
    _model = None
    _model_loaded = False
    
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
            model_path = os.path.join(base_dir, "models", "predictive_maintenance_xgboost.pkl")
            
            self._model = joblib.load(model_path)
            self._model_loaded = True
            logger.info(f"Model loaded successfully from {model_path}")
            
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
            # Create input dataframe
            input_data = pd.DataFrame({
                "Type": [machine_type],
                "Air temperature [K]": [air_temperature],
                "Process temperature [K]": [process_temperature],
                "Rotational speed [rpm]": [rotational_speed],
                "Torque [Nm]": [torque],
                "Tool wear [min]": [tool_wear]
            })
            
            # Make prediction
            prediction = self._model.predict(input_data)[0]
            probability = self._model.predict_proba(input_data)[0][1] * 100
            
            # Convert prediction to human-readable result
            if prediction == 1:
                result = "Machine Failure"
            else:
                result = "No Machine Failure"
            
            logger.info(f"Prediction: {result} (probability: {probability:.2f}%)")
            
            return result, probability
            
        except Exception as e:
            logger.error(f"Prediction error: {str(e)}")
            raise
