# Quick Start Guide

## Running the Application

### 1. Start the Web Application

```bash
cd /Users/a.sriram/Documents/MachineFailureProject/MachineFailure
source venv/bin/activate
python app.py
```

Then open your browser to: **http://localhost:5001**

### 2. Use the CLI Tool

```bash
cd /Users/a.sriram/Documents/MachineFailureProject/MachineFailure
source venv/bin/activate
python src/prediction.py
```

Follow the prompts to enter machine parameters.

### 3. Run Tests

```bash
cd /Users/a.sriram/Documents/MachineFailureProject/MachineFailure
source venv/bin/activate
python test_app.py
```

---

## What to Try

### Test the Validation
1. Open http://localhost:5001
2. Try entering invalid values:
   - Air Temperature: 500 (should show error: must be 290-310)
   - Torque: -10 (should show error: must be 0-100)
3. See real-time error messages appear

### Experience the Animations
1. Watch the stat cards fade in when page loads
2. Hover over stat cards (they lift up)
3. Enter valid data and submit
4. Watch the loading spinner appear
5. See the result reveal with bounce animation
6. Scroll down to see sections fade in

### Test Form Features
1. Submit a prediction
2. Notice your values are preserved
3. Click "Clear Form" to reset
4. Try on mobile (resize browser)

### Test Error Handling
1. Enter all valid data except one field
2. Submit the form
3. See the error alert at the top
4. Fix the error and resubmit

---

## Example Valid Inputs

**Low-Risk Machine:**
- Machine Type: M
- Air Temperature: 300
- Process Temperature: 310
- Rotational Speed: 1500
- Torque: 40
- Tool Wear: 50

**High-Risk Machine:**
- Machine Type: L
- Air Temperature: 305
- Process Temperature: 315
- Rotational Speed: 1200
- Torque: 75
- Tool Wear: 200

---

## Updating Configuration

To change model metrics:

1. Edit `config/model_config.json`
2. Update values in the `metrics` section
3. Restart the app
4. Metrics on the page will update automatically

---

## Project Structure

```
MachineFailure/
├── app.py                 # Flask application (start here)
├── services/              # Business logic
│   ├── prediction_service.py
│   └── validation_service.py
├── config/                # Configuration
│   └── model_config.json
├── static/                # Frontend assets
│   ├── style.css
│   └── js/main.js
├── templates/             # HTML templates
│   └── index.html
├── models/                # Trained models
│   └── predictive_maintenance_xgboost.pkl
├── src/                   # CLI tool
│   └── prediction.py
└── test_app.py           # Tests
```

---

## Troubleshooting

### Model Not Loading
**Error:** "Prediction model is not available"
**Solution:** Check that `models/predictive_maintenance_xgboost.pkl` exists

### Virtual Environment Issues
**Error:** "No module named 'flask'"
**Solution:** Make sure you activated the venv:
```bash
source venv/bin/activate
```

### Port Already in Use
**Error:** "Address already in use"
**Solution:** Change port in `app.py`:
```python
app.run(debug=True, port=5002)  # Use different port
```

### Animations Not Working
**Issue:** Animations appear instant
**Check:** Some browsers/OSes have reduced motion enabled
**Note:** This is intentional for accessibility

---

## Features to Explore

✓ **Real-time Validation** - Type invalid values and see instant feedback
✓ **Loading States** - Submit and watch the spinner
✓ **Smooth Animations** - Hover, click, scroll to see effects
✓ **Form Preservation** - Values stay after submission
✓ **Easy Reset** - Clear Form button
✓ **Error Handling** - Try edge cases, see graceful failures
✓ **Mobile Responsive** - Resize browser or use phone
✓ **Configuration-Driven** - Edit JSON to update metrics
✓ **CLI Tool** - Use prediction service from command line
✓ **Comprehensive Logs** - Check console for detailed logs

---

## Next Steps

1. **Customize**: Edit `config/model_config.json` to update metrics
2. **Extend**: Add new features using the service layer pattern
3. **Deploy**: Ready for production with proper error handling
4. **Monitor**: Use the logging system to track usage
5. **Test**: Add more test cases to `test_app.py`

---

## Need Help?

**Documentation:**
- `REFACTOR_SUMMARY.md` - Detailed changes
- `CHANGES.md` - Quick comparison
- This file - Quick start

**Code:**
- All services have docstrings
- Functions have clear comments
- Configuration is documented in JSON

---

## Key Files to Know

- **`app.py`** - Flask routes, main entry point
- **`services/prediction_service.py`** - Model loading & predictions
- **`services/validation_service.py`** - Input validation rules
- **`config/model_config.json`** - Metrics and settings
- **`static/js/main.js`** - Client-side validation & animations
- **`static/style.css`** - All styles and animations

---

**Enjoy your refactored application! 🚀**
