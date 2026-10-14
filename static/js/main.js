// ==================== INPUT VALIDATION ====================

// Labels and units for messages. The min/max limits come from each input's
// min/max attributes, which the server fills in from validation_service.py
const VALIDATION_RULES = {
    air_temperature: { unit: 'K', label: 'Air Temperature' },
    process_temperature: { unit: 'K', label: 'Process Temperature' },
    rotational_speed: { unit: 'RPM', label: 'Rotational Speed' },
    torque: { unit: 'Nm', label: 'Torque' },
    tool_wear: { unit: 'min', label: 'Tool Wear' }
};

// Initialize validation on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeValidation();
    initializeFormControls();
});

function initializeValidation() {
    const form = document.querySelector('form');
    
    if (!form) return;

    // Add real-time validation to each input
    Object.keys(VALIDATION_RULES).forEach(fieldName => {
        const input = form.querySelector(`[name="${fieldName}"]`);
        
        if (input) {
            // Validate on blur
            input.addEventListener('blur', function() {
                validateField(this);
            });

            // Clear error on focus
            input.addEventListener('focus', function() {
                clearFieldError(this);
            });

            // Validate on input (for instant feedback)
            input.addEventListener('input', function() {
                if (this.classList.contains('input-error')) {
                    validateField(this);
                }
            });
        }
    });

    // Validate entire form on submit
    form.addEventListener('submit', function(e) {
        if (!validateForm()) {
            e.preventDefault();
            showFormError('Please fix the errors above before submitting.');
        } else {
            showLoadingState();
        }
    });
}

function validateField(input) {
    const fieldName = input.name;
    const value = parseFloat(input.value);
    const rules = VALIDATION_RULES[fieldName];

    // Clear previous error
    clearFieldError(input);

    // Number inputs report text like "abc" as an empty value, so check badInput first
    if (input.validity && input.validity.badInput) {
        showFieldError(input, `${rules.label} must be a valid number.`);
        return false;
    }

    // Check if value is empty
    if (input.value.trim() === '') {
        showFieldError(input, `${rules.label} is required.`);
        return false;
    }

    // Check if value is a valid number
    if (isNaN(value)) {
        showFieldError(input, `${rules.label} must be a valid number.`);
        return false;
    }

    // Check range (the range the model was trained on)
    const min = parseFloat(input.min);
    const max = parseFloat(input.max);
    if (value < min || value > max) {
        showFieldError(input, `${rules.label} must be between ${min} and ${max} ${rules.unit}.`);
        return false;
    }

    // Mark as valid
    input.classList.add('input-valid');
    return true;
}

function validateForm() {
    const form = document.querySelector('form');
    let isValid = true;

    // Validate all fields
    Object.keys(VALIDATION_RULES).forEach(fieldName => {
        const input = form.querySelector(`[name="${fieldName}"]`);
        if (input && !validateField(input)) {
            isValid = false;
        }
    });

    return isValid;
}

function showFieldError(input, message) {
    input.classList.add('input-error');
    input.classList.remove('input-valid');

    // Create or update error message element
    let errorElement = input.parentElement.querySelector('.error-message');
    
    if (!errorElement) {
        errorElement = document.createElement('div');
        errorElement.className = 'error-message';
        input.parentElement.appendChild(errorElement);
    }

    errorElement.textContent = message;
}

function clearFieldError(input) {
    input.classList.remove('input-error');
    
    const errorElement = input.parentElement.querySelector('.error-message');
    if (errorElement) {
        errorElement.remove();
    }
}

function showFormError(message) {
    // Remove existing form error if present
    const existingError = document.querySelector('.form-error');
    if (existingError) {
        existingError.remove();
    }

    const form = document.querySelector('form');
    const errorDiv = document.createElement('div');
    errorDiv.className = 'form-error';
    errorDiv.textContent = message;
    
    form.insertBefore(errorDiv, form.firstChild);

    errorDiv.scrollIntoView({ block: 'center' });

    // Remove after 5 seconds
    setTimeout(() => {
        errorDiv.remove();
    }, 5000);
}


// ==================== LOADING STATE ====================

function showLoadingState() {
    const submitButton = document.querySelector('.predict-btn');

    if (!submitButton) return;

    submitButton.disabled = true;

    const buttonText = submitButton.querySelector('span:first-child');
    if (buttonText) {
        buttonText.textContent = 'Analyzing…';
    }
}


// Re-enable the button if the page is restored from the back/forward cache
window.addEventListener('pageshow', function(e) {
    if (!e.persisted) return;

    const submitButton = document.querySelector('.predict-btn');
    if (submitButton) {
        submitButton.disabled = false;
        submitButton.querySelector('span:first-child').textContent = 'Analyze machine health';
    }
});


// ==================== FORM CONTROLS ====================

function initializeFormControls() {
    addResetButton();
}

function addResetButton() {
    const form = document.querySelector('form');
    const submitButton = form.querySelector('.predict-btn');

    if (!submitButton || document.querySelector('.reset-btn')) return;

    // Create reset button
    const resetButton = document.createElement('button');
    resetButton.type = 'button';
    resetButton.className = 'reset-btn';
    resetButton.innerHTML = `
        <span>Clear</span>
        <span aria-hidden="true">↻</span>
    `;

    // Insert after submit button
    submitButton.parentElement.appendChild(resetButton);

    // Add reset functionality
    resetButton.addEventListener('click', function() {
        // form.reset() would restore the server-rendered values, so empty fields directly
        form.querySelectorAll('input').forEach(input => {
            input.value = '';
        });
        form.querySelector('select[name="machine_type"]').value = 'M';
        
        // Clear all validation states
        form.querySelectorAll('.input-error, .input-valid').forEach(input => {
            input.classList.remove('input-error', 'input-valid');
        });

        // Clear all error messages
        form.querySelectorAll('.error-message').forEach(error => {
            error.remove();
        });

        // Clear form error
        const formError = document.querySelector('.form-error');
        if (formError) {
            formError.remove();
        }

        clearPrediction();
    });
}

// Return the result panel, stat cells and sensor chart to the "no prediction" state
function clearPrediction() {
    const panel = document.querySelector('.result-panel');
    if (panel) {
        panel.querySelectorAll('.error-alert, .verdict, .probability, .failure-modes')
            .forEach(el => el.remove());

        const template = document.getElementById('empty-result-template');
        if (template && !panel.querySelector('.empty-result')) {
            panel.insertBefore(template.content.cloneNode(true), template);
        }
    }

    document.querySelectorAll('.stat-number').forEach(el => {
        el.textContent = '–';
    });

    if (window.sensorChart) {
        const canvas = window.sensorChart.canvas;
        window.sensorChart.destroy();
        window.sensorChart = null;

        const placeholder = document.createElement('p');
        placeholder.className = 'chart-empty';
        placeholder.textContent = 'Run a prediction to see the current readings.';
        canvas.replaceWith(placeholder);
    }

    // Turn the POST result page into a plain GET entry so a refresh doesn't resubmit
    history.replaceState(null, '', window.location.pathname + window.location.hash);
}


// ==================== NAVIGATION ====================

// Highlight the nav link of the section currently in view
document.addEventListener('DOMContentLoaded', function() {
    const links = document.querySelectorAll('.site-header nav a');
    const sections = document.querySelectorAll('section[id]');

    function updateActiveLink() {
        let current = 'dashboard';
        sections.forEach(section => {
            if (window.scrollY >= section.offsetTop - 120) {
                current = section.id;
            }
        });
        // The last section may be too short to reach the top of the viewport
        if (window.innerHeight + window.scrollY >= document.body.scrollHeight - 2 && sections.length) {
            current = sections[sections.length - 1].id;
        }
        links.forEach(link => {
            link.classList.toggle('active', link.getAttribute('href') === '#' + current);
        });
    }

    window.addEventListener('scroll', updateActiveLink, { passive: true });
    // The browser may jump to #prediction after this script runs, without a scroll event
    window.addEventListener('load', updateActiveLink);
    window.addEventListener('hashchange', updateActiveLink);
    updateActiveLink();
});
