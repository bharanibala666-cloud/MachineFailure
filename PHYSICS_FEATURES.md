# Physics-Informed Features — What Changed and Why

## One-line summary

Instead of making the model bigger, we made the **inputs smarter**: the same 6 sensor
readings are converted into the 3 physical quantities that actually cause machine failure.

## Before vs After

| | Original model | Physics-informed model |
|---|---|---|
| User inputs | 6 (Type, 2 temps, RPM, torque, tool wear) | **Same 6** |
| What the model sees | Raw readings | Power, Temp diff, Strain, Tool wear, RPM, Type |
| Algorithm | XGBoost (200 trees, depth 5) | **Same XGBoost settings** |
| Decision threshold | 0.5 (default) | 0.35 (picked by 5-fold CV on training data only) |
| Output | Fail / no fail + probability | Fail / no fail + probability + **which failure mode and why** |

## The three physics features

| Feature | Formula | Failure it explains | Documented limit |
|---|---|---|---|
| **Power [W]** | Torque × RPM × 2π/60 | Power failure (PWF) | Fails below 3,500 W or above 9,000 W |
| **Temp diff [K]** | Process temp − Air temp | Heat dissipation failure (HDF) | Fails if < 8.6 K **and** RPM < 1,380 |
| **Strain [min·Nm]** | Tool wear × Torque | Overstrain failure (OSF) | Fails above 11,000 (L) / 12,000 (M) / 13,000 (H) |

**Why the raw model struggles:** a power failure happens when *torque × speed* is too
high or too low. Neither torque nor speed alone tells you that. A high torque is fine at
low speed and dangerous at high speed. A tree model can only split on one column at a
time, so it has to piece the product together from many small splits. That uses up model
capacity and never quite works. Giving it the product directly turns a hard problem into one split.

## Results (test set: 2,000 machines, 68 actual failures)

From `python train_model.py`:

| Metric | Original | Physics | Change |
|---|---|---|---|
| Accuracy | 98.65 % | **99.25 %** | +0.6 |
| Precision | 88.68 % | **93.44 %** | +4.8 |
| Recall | 69.12 % | **83.82 %** | **+14.7** |
| F1-Score | 77.69 % | **88.37 %** | **+10.7** |
| ROC-AUC | 97.65 % | **98.86 %** | +1.2 |
| Missed failures | 21 | **11** | **−48 %** |
| False alarms | 6 | **4** | −2 |

From `python experiment_feature_comparison.py` (all at threshold 0.5, plus 5-fold CV):

| Model | Test F1 | 5-fold CV F1 |
|---|---|---|
| Raw XGBoost (original) | 77.69 % | 72.14 % |
| Physics XGBoost | 84.80 % | 83.41 % |
| Physics **Decision Tree** (depth 6) | 86.67 % | **89.11 %** |

So with physics features, **a single decision tree beats the original XGBoost ensemble.**
Better features matter more than a more complex model.

## Why accuracy alone is misleading

Only 3.39 % of machines fail. A "model" that always says *no failure* gets **96.61 %
accuracy** while catching zero failures. That is why we report **Recall** (how many
real failures we catch) and **F1** (balance of recall and precision).

## Proof the model learned real physics

A depth-4 decision tree trained on the physics features chooses these split points by itself:

```
Strain <= 10,998   (documented limit: 11,000)
Power  <= 3,496 W  (documented limit:  3,500 W)
Power  >  9,004 W  (documented limit:  9,000 W)
Temp diff <= 8.65 K (documented limit: 8.6 K)
```

Nobody gave the model these numbers. It recovered the engineering limits from data alone.

## Explainable predictions in the app

Each prediction now shows a **failure-mode check**. Every mechanism is marked *OK*,
*Near limit* (within 10 %) or *At risk*. Example:

> Power 9,410 W is above the 9,000 W maximum → **At risk**
> Strain 10,450 is close to the type-L limit of 11,000 → **Near limit**

The operator learns *what to fix*, e.g. reduce load or replace the tool, not just
that the machine "may fail".

## Honest limitations

- The physics model still misses 11 failures. Most are **tool-wear failures (TWF)**,
  which the dataset triggers at a **random** time between 200 and 240 min of wear.
  No model can predict a random event exactly. The app flags tool wear ≥ 200 min as *At risk*.
- The AI4I 2020 dataset is synthetic. Its failure rules are published, so the physics
  features fit it very well. On real machines the same idea applies: power, thermal
  margin and accumulated load are standard engineering indicators. The exact limits
  would come from the machine's datasheet.
- The "leakage" model (99.8 % accuracy) uses the failure-type labels as inputs. Those
  are only known *after* a failure, so it can't be deployed. It is shown only as an upper bound.

## Likely viva questions

**"Other projects use many models and complex pipelines. How is yours better?"**
They add complexity to the *model*. We add knowledge to the *features*. Our pipeline has
one extra step (3 formulas). It cuts missed failures by about half, and every
prediction can be explained.

**"Isn't feature engineering cheating?"**
No. All three features are computed only from the 6 sensor values available *before* a
failure. No labels are used. Any real maintenance engineer would compute power and temperature margin.

**"How did you choose the 0.35 threshold?"**
With 5-fold cross-validation on the training set only, picking the threshold with the best F1.
The test set was never used for tuning. A lower threshold catches more failures. In
maintenance, a missed failure costs much more than an extra inspection.

**"Why not just use the rules directly?"**
The rules come from the dataset's documentation. Real machines don't come with
such clean rules. The ML model *learns* the limits from data and also handles cases near the limits.

## Files

| File | Purpose |
|---|---|
| `services/feature_engineering.py` | Physics formulas, sklearn pipeline, failure-mode explanations |
| `train_model.py` | Trains the deployed model, tunes threshold, updates `config/model_config.json` |
| `experiment_feature_comparison.py` | Full comparison, CV, decision-tree rules, confusion matrices |
| `models/predictive_maintenance_xgboost_physics.pkl` | Deployed model |
| `results/physics_vs_baseline.csv` | Before/after metrics |
| `results/feature_comparison_results.txt` | Full experiment output |
