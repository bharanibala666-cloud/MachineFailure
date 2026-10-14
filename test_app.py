"""
Test script for the refactored application
"""
import sys
from services.prediction_service import PredictionService
from services.validation_service import ValidationService

def test_services():
    """Test all services are working correctly"""
    print("=" * 60)
    print("Testing Refactored Application")
    print("=" * 60)
    print()
    
    # Test 1: Prediction Service
    print("Test 1: Prediction Service Initialization")
    try:
        prediction_service = PredictionService()
        assert prediction_service.is_model_loaded(), "Model should be loaded"
        print("✓ Prediction service initialized successfully")
        print(f"✓ Model loaded: {prediction_service.is_model_loaded()}")
    except Exception as e:
        print(f"✗ Failed: {str(e)}")
        return False
    print()
    
    # Test 2: Validation Service
    print("Test 2: Validation Service")
    try:
        validation_service = ValidationService()
        
        # Test valid inputs
        is_valid, errors = validation_service.validate_all_inputs(
            machine_type='M',
            air_temperature=300.0,
            process_temperature=310.0,
            rotational_speed=1500,
            torque=40.0,
            tool_wear=100
        )
        assert is_valid, "Valid inputs should pass validation"
        print("✓ Valid inputs pass validation")
        
        # Test invalid inputs
        is_valid, errors = validation_service.validate_all_inputs(
            machine_type='X',  # Invalid
            air_temperature=1000,  # Out of range
            process_temperature=310.0,
            rotational_speed=1500,
            torque=40.0,
            tool_wear=100
        )
        assert not is_valid, "Invalid inputs should fail validation"
        assert len(errors) > 0, "Should have validation errors"
        print("✓ Invalid inputs fail validation as expected")
        print(f"  Errors detected: {len(errors)}")
    except Exception as e:
        print(f"✗ Failed: {str(e)}")
        return False
    print()
    
    # Test 3: End-to-end prediction
    print("Test 3: End-to-End Prediction")
    try:
        result, probability = prediction_service.predict(
            machine_type='M',
            air_temperature=300.0,
            process_temperature=310.0,
            rotational_speed=1500,
            torque=40.0,
            tool_wear=100
        )
        assert result in ["Machine Failure", "No Machine Failure"], "Result should be valid"
        assert 0 <= probability <= 100, "Probability should be between 0 and 100"
        print("✓ Prediction successful")
        print(f"  Result: {result}")
        print(f"  Probability: {probability:.2f}%")
    except Exception as e:
        print(f"✗ Failed: {str(e)}")
        return False
    print()
    
    # Test 4: Configuration loading
    print("Test 4: Configuration Loading")
    try:
        import json
        import os
        
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'model_config.json')
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        assert 'metrics' in config, "Config should have metrics"
        assert 'model' in config, "Config should have model info"
        print("✓ Configuration loaded successfully")
        print(f"  Model: {config['model']['name']}")
        print(f"  Accuracy: {config['metrics']['accuracy']}%")
    except Exception as e:
        print(f"✗ Failed: {str(e)}")
        return False
    print()
    
    # Test 5: Physics feature engineering
    print("Test 5: Physics Feature Engineering")
    try:
        import pandas as pd
        from services.feature_engineering import (
            add_physics_features, explain_failure_modes, POWER, TEMP_DIFF, STRAIN
        )

        row = pd.DataFrame({
            "Torque [Nm]": [40.0],
            "Rotational speed [rpm]": [1500],
            "Air temperature [K]": [300.0],
            "Process temperature [K]": [310.0],
            "Tool wear [min]": [100],
        })
        features = add_physics_features(row).iloc[0]
        assert abs(features[POWER] - 6283.19) < 0.1, "Power = T x rpm x 2pi/60"
        assert abs(features[TEMP_DIFF] - 10.0) < 1e-9, "Temp diff = process - air"
        assert features[STRAIN] == 4000, "Strain = wear x torque"
        print("✓ Power, Temp diff and Strain computed correctly")

        def statuses(**kwargs):
            return {m["code"]: m["status"] for m in explain_failure_modes(**kwargs)}

        normal = statuses(machine_type='M', air_temperature=300.0, process_temperature=310.0,
                          rotational_speed=1500, torque=40.0, tool_wear=100)
        assert set(normal.values()) == {"ok"}, f"Normal machine should be all OK: {normal}"

        overpowered = statuses(machine_type='M', air_temperature=300.0, process_temperature=310.0,
                               rotational_speed=1500, torque=65.0, tool_wear=100)
        assert overpowered["PWF"] == "risk", "Power above 9000 W should be a risk"

        overheated = statuses(machine_type='M', air_temperature=302.0, process_temperature=310.0,
                              rotational_speed=1300, torque=40.0, tool_wear=100)
        assert overheated["HDF"] == "risk", "Small temp gap at low rpm should be a risk"

        overstrained = statuses(machine_type='L', air_temperature=300.0, process_temperature=310.0,
                                rotational_speed=1500, torque=55.0, tool_wear=210)
        assert overstrained["OSF"] == "risk", "Strain above type-L limit should be a risk"
        assert overstrained["TWF"] == "risk", "Tool wear above 200 min should be a risk"
        print("✓ Failure-mode explanations flag the right risks")

        result, probability = prediction_service.predict(
            machine_type='L', air_temperature=300.0, process_temperature=310.0,
            rotational_speed=1500, torque=55.0, tool_wear=210
        )
        assert result == "Machine Failure", "Overstrained machine should be predicted to fail"
        print(f"✓ Overstrained machine predicted as failure ({probability:.2f}%)")
    except Exception as e:
        print(f"✗ Failed: {str(e)}")
        return False
    print()

    print("=" * 60)
    print("All Tests Passed! ✓")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_services()
    sys.exit(0 if success else 1)
