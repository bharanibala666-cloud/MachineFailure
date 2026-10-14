// ==================== INPUT VALIDATION ====================

// Validation ranges based on dataset analysis
const VALIDATION_RULES = {
    air_temperature: {
        min: 290,
        max: 310,
        unit: 'K',
        label: 'Air Temperature'
    },
    process_temperature: {
        min: 300,
        max: 320,
        unit: 'K',
        label: 'Process Temperature'
    },
    rotational_speed: {
        min: 1000,
        max: 3000,
        unit: 'RPM',
        label: 'Rotational Speed'
    },
    torque: {
        min: 0,
        max: 100,
        unit: 'Nm',
        label: 'Torque'
    },
    tool_wear: {
        min: 0,
        max: 300,
        unit: 'min',
        label: 'Tool Wear'
    }
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

    // Check range
    if (value < rules.min || value > rules.max) {
        showFieldError(input, `${rules.label} must be between ${rules.min} and ${rules.max} ${rules.unit}.`);
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

    // Scroll to form error
    errorDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });

    // Remove after 5 seconds
    setTimeout(() => {
        errorDiv.remove();
    }, 5000);
}


// ==================== LOADING STATE ====================

function showLoadingState() {
    const submitButton = document.querySelector('.predict-btn');
    
    if (!submitButton) return;

    // Disable button
    submitButton.disabled = true;
    submitButton.classList.add('loading');

    // Change button text
    const buttonText = submitButton.querySelector('span:first-child');
    if (buttonText) {
        buttonText.textContent = 'Analyzing...';
    }

    // Create loading overlay
    const overlay = document.createElement('div');
    overlay.className = 'loading-overlay';
    overlay.innerHTML = `
        <div class="loading-spinner">
            <div class="spinner"></div>
            <p>Analyzing Machine Health...</p>
        </div>
    `;
    
    document.body.appendChild(overlay);

    // Show overlay with animation
    setTimeout(() => {
        overlay.classList.add('visible');
    }, 10);
}


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
        <span>Clear Form</span>
        <span class="reset-icon">↻</span>
    `;

    // Insert after submit button
    submitButton.parentElement.appendChild(resetButton);

    // Add reset functionality
    resetButton.addEventListener('click', function() {
        form.reset();
        
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

        // Add feedback animation
        resetButton.classList.add('reset-active');
        setTimeout(() => {
            resetButton.classList.remove('reset-active');
        }, 300);
    });
}


// ==================== SMOOTH SCROLLING ====================

// Smooth scroll for navigation links
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('nav a').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            const targetSection = document.querySelector(targetId);
            
            if (targetSection) {
                targetSection.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
                
                // Update active link
                document.querySelectorAll('nav a').forEach(link => {
                    link.classList.remove('active');
                });
                this.classList.add('active');
            }
        });
    });

    // Intersection Observer for scroll animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -100px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('is-visible');
            }
        });
    }, observerOptions);

    // Observe sections for animation
    document.querySelectorAll('#analytics, #models').forEach(section => {
        section.classList.add('fade-in-section');
        observer.observe(section);
    });

    // Update active nav on scroll
    window.addEventListener('scroll', () => {
        let current = '';
        const sections = document.querySelectorAll('section');
        
        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.clientHeight;
            if (pageYOffset >= (sectionTop - 150)) {
                current = section.getAttribute('id');
            }
        });

        document.querySelectorAll('nav a').forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === '#' + current) {
                link.classList.add('active');
            }
        });
    });
});


// ==================== ENHANCED ANIMATIONS ====================

document.addEventListener('DOMContentLoaded', function() {
    // Animate charts when they're created
    animateCharts();
    
    // Add ripple effect to buttons
    addRippleEffect();
    
    // Enhanced scroll reveal
    enhancedScrollReveal();
});

function animateCharts() {
    // Chart.js animations are already configured in the HTML
    // But we can add entrance animations to canvas elements
    const canvases = document.querySelectorAll('canvas');
    canvases.forEach((canvas, index) => {
        canvas.style.opacity = '0';
        canvas.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            canvas.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            canvas.style.opacity = '1';
            canvas.style.transform = 'translateY(0)';
        }, 400 + (index * 100));
    });
}

function addRippleEffect() {
    const buttons = document.querySelectorAll('.predict-btn, .reset-btn');
    
    buttons.forEach(button => {
        button.addEventListener('click', function(e) {
            // Only add ripple if not disabled
            if (this.disabled) return;
            
            const ripple = document.createElement('span');
            ripple.className = 'ripple';
            
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            
            this.appendChild(ripple);
            
            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    });
}

function enhancedScrollReveal() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('is-visible');
                
                // Stagger child elements if they exist
                const children = entry.target.querySelectorAll('.chart-panel, .metric-card');
                children.forEach((child, index) => {
                    setTimeout(() => {
                        child.style.opacity = '1';
                        child.style.transform = 'translateY(0)';
                    }, index * 100);
                });
            }
        });
    }, observerOptions);

    // Observe all sections
    document.querySelectorAll('section').forEach(section => {
        if (!section.classList.contains('fade-in-section')) {
            section.classList.add('fade-in-section');
        }
        observer.observe(section);
    });
}


// ==================== ENHANCED FORM INTERACTIONS ====================

// Add floating label effect
document.addEventListener('DOMContentLoaded', function() {
    const inputs = document.querySelectorAll('.input-group input, .input-group select');
    
    inputs.forEach(input => {
        // Add focus class for animations
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('input-focused');
        });
        
        input.addEventListener('blur', function() {
            this.parentElement.classList.remove('input-focused');
        });
    });
});


// ==================== PROGRESS BAR ANIMATION ====================

// Animate progress bar when it appears
document.addEventListener('DOMContentLoaded', function() {
    const progressBar = document.querySelector('.progress-bar');
    
    if (progressBar) {
        // Trigger reflow to restart animation
        progressBar.style.animation = 'none';
        
        setTimeout(() => {
            progressBar.style.animation = null;
        }, 10);
    }
});
