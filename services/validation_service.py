"""
Validation Service - Handles input validation
"""
import logging
import math

logger = logging.getLogger(__name__)


# Validation ranges = the range covered by the AI4I 2020 training data,
# rounded slightly outward. Outside these the model would be extrapolating
# and its predictions are unreliable.
#   Air temp 295.3-304.5 K | Process temp 305.7-313.8 K | Speed 1168-2886 rpm
#   Torque 3.8-76.6 Nm     | Tool wear 0-253 min
VALIDATION_RULES = {
    'air_temperature': {
        'min': 295,
        'max': 305,
        'label': 'Air Temperature',
        'unit': 'K'
    },
    'process_temperature': {
        'min': 305,
        'max': 314,
        'label': 'Process Temperature',
        'unit': 'K'
    },
    'rotational_speed': {
        'min': 1150,
        'max': 2900,
        'label': 'Rotational Speed',
        'unit': 'RPM'
    },
    'torque': {
        'min': 3.5,
        'max': 77,
        'label': 'Torque',
        'unit': 'Nm'
    },
    'tool_wear': {
        'min': 0,
        'max': 255,
        'label': 'Tool Wear',
        'unit': 'min'
    }
}

VALID_MACHINE_TYPES = ['L', 'M', 'H']


class ValidationService:
    """Service for validating user inputs"""
    
    @staticmethod
    def validate_numeric_field(field_name, value):
        """
        Validate a numeric input field
        
        Args:
            field_name (str): Name of the field (e.g., 'air_temperature')
            value: Value to validate
            
        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        """
        rules = VALIDATION_RULES.get(field_name)
        
        if not rules:
            logger.warning(f"No validation rules found for field: {field_name}")
            return True, None
        
        # Check the field was filled in
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return False, f"{rules['label']} is required"
        
        # Check if value is numeric (NaN/inf parse as floats but are not usable)
        try:
            num_value = float(value)
        except (ValueError, TypeError):
            return False, f"{rules['label']} must be a valid number"
        
        if not math.isfinite(num_value):
            return False, f"{rules['label']} must be a valid number"
        
        # Check range
        if num_value < rules['min'] or num_value > rules['max']:
            error_msg = (f"{rules['label']} must be between "
                        f"{rules['min']} and {rules['max']} {rules['unit']}")
            return False, error_msg
        
        return True, None
    
    @staticmethod
    def validate_machine_type(machine_type):
        """
        Validate machine type
        
        Args:
            machine_type (str): Machine type to validate
            
        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        """
        if not machine_type:
            return False, "Machine type is required"
        
        machine_type = machine_type.upper()
        
        if machine_type not in VALID_MACHINE_TYPES:
            error_msg = f"Machine type must be one of: {', '.join(VALID_MACHINE_TYPES)}"
            return False, error_msg
        
        return True, None
    
    @staticmethod
    def validate_all_inputs(machine_type, air_temperature, process_temperature,
                           rotational_speed, torque, tool_wear):
        """
        Validate all prediction inputs
        
        Args:
            machine_type (str): Type of machine
            air_temperature: Air temperature value
            process_temperature: Process temperature value
            rotational_speed: Rotational speed value
            torque: Torque value
            tool_wear: Tool wear value
            
        Returns:
            tuple: (is_valid: bool, error_messages: list)
        """
        errors = []
        
        # Validate machine type
        is_valid, error_msg = ValidationService.validate_machine_type(machine_type)
        if not is_valid:
            errors.append(error_msg)
        
        # Validate numeric fields
        numeric_fields = {
            'air_temperature': air_temperature,
            'process_temperature': process_temperature,
            'rotational_speed': rotational_speed,
            'torque': torque,
            'tool_wear': tool_wear
        }
        
        for field_name, value in numeric_fields.items():
            is_valid, error_msg = ValidationService.validate_numeric_field(field_name, value)
            if not is_valid:
                errors.append(error_msg)
        
        is_all_valid = len(errors) == 0
        return is_all_valid, errors
    
    @staticmethod
    def get_validation_rules():
        """Get validation rules for client-side validation"""
        return VALIDATION_RULES
