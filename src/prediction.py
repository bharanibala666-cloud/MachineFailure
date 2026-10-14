"""
CLI Prediction Tool - Command-line interface for machine failure prediction
Uses shared prediction service from the web application
"""
import sys
import os

# Add parent directory to path to import services
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.prediction_service import PredictionService
from services.validation_service import ValidationService


def main():
    """Main CLI function"""
    print("=" * 50)
    print("  Predictive Maintenance System - CLI")
    print("=" * 50)
    print()
    
    # Initialize services
    try:
        prediction_service = PredictionService()
        validation_service = ValidationService()
        
        if not prediction_service.is_model_loaded():
            print("ERROR: Model failed to load. Cannot proceed.")
            return
        
        print("✓ Model loaded successfully")
        print()
        
    except Exception as e:
        print(f"ERROR: Failed to initialize services: {str(e)}")
        return
    
    # Get user input
    try:
        print("Please enter machine parameters:")
        print()
        
        machine_type = input("Machine type (L/M/H): ").upper().strip()
        
        # Validate machine type immediately
        is_valid, error_msg = validation_service.validate_machine_type(machine_type)
        if not is_valid:
            print(f"ERROR: {error_msg}")
            return
        
        air_temperature = float(input("Air temperature [K]: ").strip())
        process_temperature = float(input("Process temperature [K]: ").strip())
        rotational_speed = float(input("Rotational speed [RPM]: ").strip())
        torque = float(input("Torque [Nm]: ").strip())
        tool_wear = float(input("Tool wear [min]: ").strip())
        
    except ValueError:
        print("ERROR: All numeric inputs must be valid numbers")
        return
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        return
    
    # Validate all inputs
    is_valid, validation_errors = validation_service.validate_all_inputs(
        machine_type=machine_type,
        air_temperature=air_temperature,
        process_temperature=process_temperature,
        rotational_speed=rotational_speed,
        torque=torque,
        tool_wear=tool_wear
    )
    
    if not is_valid:
        print()
        print("VALIDATION ERRORS:")
        for error in validation_errors:
            print(f"  • {error}")
        return
    
    # Make prediction
    try:
        result, probability = prediction_service.predict(
            machine_type=machine_type,
            air_temperature=air_temperature,
            process_temperature=process_temperature,
            rotational_speed=rotational_speed,
            torque=torque,
            tool_wear=tool_wear
        )
        
        # Display results
        print()
        print("=" * 50)
        print("  PREDICTION RESULT")
        print("=" * 50)
        print()
        print(f"Prediction:           {result}")
        print(f"Failure Probability:  {probability:.2f}%")
        print()
        
        # Visual indicator
        if result == "Machine Failure":
            print("⚠  WARNING: Machine may fail soon!")
            print("   Recommended action: Schedule maintenance")
        else:
            print("✓  Machine is operating normally")
            print("   No immediate action required")
        
        print()
        
    except Exception as e:
        print(f"ERROR: Prediction failed: {str(e)}")
        return


if __name__ == "__main__":
    main()
