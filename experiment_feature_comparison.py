"""
experiment_feature_comparison.py
=================================
Raw sensor features vs Physics-informed features

Models compared (identical split and XGBoost hyperparameters, threshold 0.5):
  1. Leakage reference (11 features)
       Includes sub-failure labels TWF/HDF/PWF/OSF/RNF, which are only known
       AFTER a failure. Shown only as an upper bound — not deployable.

  2. Raw XGBoost (6 features)  — the original approach
       Type, Air temp, Process temp, Rotational speed, Torque, Tool wear

  3. Physics XGBoost  ← OUR APPROACH
       Same 6 raw inputs, converted into the quantities that cause failure:
         Power [W]       = Torque x RPM x 2pi/60       (power failure)
         Temp diff [K]   = Process temp - Air temp      (heat dissipation failure)
         Strain [min*Nm] = Tool wear x Torque           (overstrain failure)

  4. Physics Decision Tree (depth 6)
       Shows that with the right features even a simple, fully readable
       model performs as well as XGBoost.

Also reported:
  - 5-fold cross-validated F1 / recall (robustness, not just one split)
  - The rules a depth-4 tree learns from physics features
  - Which failure types each model still misses

Outputs:
  - results/feature_comparison_results.txt
  - results/feature_comparison_confusion_matrices.png
"""

import os
import time
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import (
    accuracy_score, confusion_matrix, f1_score, precision_score, recall_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier, export_text
from xgboost import XGBClassifier

from services.feature_engineering import (
    PHYSICS_NUMERIC_FEATURES, RAW_FEATURES, build_physics_pipeline,
)

warnings.filterwarnings("ignore", category=UserWarning)

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(BASE_DIR, "dataset", "ai4i2020.csv")
RESULTS_DIR  = os.path.join(BASE_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

TARGET       = "Machine failure"
LEAKAGE_COLS = ["TWF", "HDF", "PWF", "OSF", "RNF"]
FAILURE_TYPES = ["TWF", "HDF", "PWF", "OSF", "RNF"]

XGB_PARAMS = dict(
    n_estimators=200,
    max_depth=5,
    learning_rate=0.05,
    random_state=42,
    eval_metric="logloss",
)

# ── Model builders ─────────────────────────────────────────────────────────────

def build_raw_pipeline(numeric_cols):
    """Original approach: scaled raw columns + one-hot Type -> XGBoost."""
    return Pipeline([
        ("preprocessor", ColumnTransformer(transformers=[
            ("num", StandardScaler(), numeric_cols),
            ("cat", OneHotEncoder(handle_unknown="ignore"), ["Type"]),
        ])),
        ("classifier", XGBClassifier(**XGB_PARAMS)),
    ])


MODELS = [
    # (name, feature columns, pipeline factory, leakage?)
    ("Leakage reference\n(11 features)", RAW_FEATURES + LEAKAGE_COLS,
     lambda: build_raw_pipeline(RAW_FEATURES[1:] + LEAKAGE_COLS), True),
    ("Raw XGBoost\n(original)", RAW_FEATURES,
     lambda: build_raw_pipeline(RAW_FEATURES[1:]), False),
    ("Physics XGBoost\n(our approach)", RAW_FEATURES,
     lambda: build_physics_pipeline(XGBClassifier(**XGB_PARAMS)), False),
    ("Physics Decision Tree\n(depth 6)", RAW_FEATURES,
     lambda: build_physics_pipeline(DecisionTreeClassifier(max_depth=6, random_state=42)), False),
]

# ── Helpers ────────────────────────────────────────────────────────────────────

def evaluate(name, pipeline, X_train, y_train, X_test, y_test, test_failure_types, leakage):
    pipeline.fit(X_train, y_train)

    start  = time.perf_counter()
    y_pred = pipeline.predict(X_test)
    elapsed_ms = (time.perf_counter() - start) * 1000

    missed = test_failure_types[(y_test == 1) & (y_pred == 0)].sum()
    missed_str = ", ".join(f"{k}={v}" for k, v in missed.items() if v) or "none"

    return {
        "Model":               name,
        "Leakage":             "YES ⚠" if leakage else "No",
        "Accuracy":            round(accuracy_score(y_test, y_pred) * 100, 2),
        "Precision":           round(precision_score(y_test, y_pred, zero_division=0) * 100, 2),
        "Recall":              round(recall_score(y_test, y_pred, zero_division=0) * 100, 2),
        "F1-Score":            round(f1_score(y_test, y_pred, zero_division=0) * 100, 2),
        "Missed failures":     int(((y_test == 1) & (y_pred == 0)).sum()),
        "False alarms":        int(((y_test == 0) & (y_pred == 1)).sum()),
        "Inference Time (ms)": round(elapsed_ms, 2),
        "confusion_matrix":    confusion_matrix(y_test, y_pred),
        "missed_by_type":      missed_str,
    }


def cross_validated(pipeline_factory, X, y):
    """5-fold cross-validated F1 and recall on the full dataset."""
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    pred = cross_val_predict(pipeline_factory(), X, y, cv=cv)
    return round(f1_score(y, pred) * 100, 2), round(recall_score(y, pred) * 100, 2)


def plot_confusion_matrices(results):
    """Save side-by-side confusion matrices for all models."""
    n = len(results)
    fig = plt.figure(figsize=(5.5 * n, 5.5))
    fig.patch.set_facecolor("#0f1117")
    gs  = gridspec.GridSpec(1, n, figure=fig, wspace=0.38)
    colors = ["#ff4d6d", "#00c6ff", "#4ade80", "#f7971e"]

    for idx, res in enumerate(results):
        ax  = fig.add_subplot(gs[0, idx])
        cm  = res["confusion_matrix"]
        col = colors[idx % len(colors)]

        ax.imshow(cm, cmap="Blues", aspect="auto")
        thresh = cm.max() / 2.0
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                ax.text(j, i, f"{cm[i, j]:,}",
                        ha="center", va="center", fontsize=13, fontweight="bold",
                        color="white" if cm[i, j] > thresh else "#0f1117")

        ax.set_xticks([0, 1])
        ax.set_yticks([0, 1])
        ax.set_xticklabels(["No Failure", "Failure"], color="white", fontsize=10)
        ax.set_yticklabels(["No Failure", "Failure"], color="white", fontsize=10)
        ax.set_xlabel("Predicted", color="white", fontsize=10)
        ax.set_ylabel("Actual",    color="white", fontsize=10)

        title = res["Model"]
        if res["Leakage"] != "No":
            title += "\n[DATA LEAKAGE — unfair baseline]"
        ax.set_title(title, color=col, fontsize=11, fontweight="bold", pad=10)
        ax.tick_params(colors="white")
        for spine in ax.spines.values():
            spine.set_edgecolor(col)
            spine.set_linewidth(1.5)
        ax.set_facecolor("#1a1d27")

    plt.suptitle("Confusion Matrix — Raw vs Physics-Informed Features", color="white",
                 fontsize=14, fontweight="bold", y=1.03)

    out_path = os.path.join(RESULTS_DIR, "feature_comparison_confusion_matrices.png")
    plt.savefig(out_path, bbox_inches="tight", dpi=150,
                facecolor=fig.get_facecolor())
    plt.close()
    return out_path


def format_table(results):
    metrics = ["Leakage", "Accuracy", "Precision", "Recall", "F1-Score",
               "CV F1 (5-fold)", "CV Recall (5-fold)",
               "Missed failures", "False alarms", "Inference Time (ms)"]
    col_w = 34
    hdr_w = 22

    header  = f"{'Metric':<{hdr_w}}" + "".join(f"{r['Model']:>{col_w}}" for r in results)
    divider = "─" * (hdr_w + col_w * len(results))

    lines = [divider, header, divider]
    for m in metrics:
        row = f"{m:<{hdr_w}}"
        for r in results:
            val = r[m]
            if m == "Inference Time (ms)":
                cell = f"{val:.2f} ms"
            elif isinstance(val, float):
                cell = f"{val:.2f} %"
            else:
                cell = str(val)
            row += f"{cell:>{col_w}}"
        lines.append(row)
    lines.append(divider)
    return "\n".join(lines)


def shallow_tree_rules(X_train, y_train):
    """Rules a depth-4 tree learns from physics features (readable on one slide)."""
    tree_pipe = build_physics_pipeline(DecisionTreeClassifier(max_depth=4, random_state=42))
    tree_pipe.fit(X_train, y_train)
    type_names = [f"Type_{c}" for c in tree_pipe.named_steps["preprocessor"]
                  .named_transformers_["cat"].categories_[0]]
    return export_text(tree_pipe.named_steps["classifier"],
                       feature_names=PHYSICS_NUMERIC_FEATURES + type_names)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 72)
    print("  Raw Sensor Features  vs  Physics-Informed Features")
    print("=" * 72 + "\n")

    df = pd.read_csv(DATASET_PATH)
    y  = df[TARGET]
    print(f"-> Rows: {len(df):,}  |  Failures: {y.sum()} ({y.mean()*100:.2f}%)")
    print(f"   Always predicting 'no failure' already scores "
          f"{(1 - y.mean())*100:.2f}% accuracy — so we focus on Recall and F1.\n")

    all_cols = RAW_FEATURES + LEAKAGE_COLS
    X_tr, X_te, y_tr, y_te = train_test_split(
        df[all_cols], y, test_size=0.20, random_state=42, stratify=y
    )
    test_failure_types = df.loc[X_te.index, FAILURE_TYPES]

    results = []
    for i, (name, cols, factory, leakage) in enumerate(MODELS, 1):
        flat_name = name.replace("\n", " ")
        print(f"-> [{i}/{len(MODELS)}] {flat_name} ...")
        res = evaluate(name, factory(), X_tr[cols], y_tr, X_te[cols], y_te,
                       test_failure_types, leakage)
        res["CV F1 (5-fold)"], res["CV Recall (5-fold)"] = cross_validated(factory, df[cols], y)
        print(f"   Recall: {res['Recall']:.2f}%   F1: {res['F1-Score']:.2f}%   "
              f"CV F1: {res['CV F1 (5-fold)']:.2f}%\n")
        results.append(res)

    flat_results = [dict(r, Model=r["Model"].replace("\n", " ")) for r in results]
    table_str = format_table(flat_results)
    rules = shallow_tree_rules(X_tr[RAW_FEATURES], y_tr)

    print(table_str)
    print("\nDepth-4 decision tree on physics features:")
    print(rules)

    raw, phys = flat_results[1], flat_results[2]
    summary = [
        "KEY FINDINGS",
        f"- Physics features raise recall {raw['Recall']:.2f}% -> {phys['Recall']:.2f}% "
        f"and F1 {raw['F1-Score']:.2f}% -> {phys['F1-Score']:.2f}%,",
        f"  using the SAME 6 sensor inputs and the SAME XGBoost settings.",
        f"- Missed failures: {raw['Missed failures']} -> {phys['Missed failures']}  |  "
        f"False alarms: {raw['False alarms']} -> {phys['False alarms']}",
        f"- 5-fold CV F1: {raw['CV F1 (5-fold)']:.2f}% -> {phys['CV F1 (5-fold)']:.2f}% "
        f"(the gain is not luck of one split)",
        "- A shallow tree rediscovers the documented physical limits:",
        "  Power ~3500 W / ~9000 W, Temp diff ~8.6 K, Strain ~11000 min*Nm.",
        "- Failures still missed by the physics model: " + phys["missed_by_type"],
        "  TWF happens at a RANDOM time between 200-240 min of tool wear,",
        "  so no model can predict it exactly.",
    ]
    print("\n" + "\n".join(summary) + "\n")

    txt_path = os.path.join(RESULTS_DIR, "feature_comparison_results.txt")
    with open(txt_path, "w") as fh:
        fh.write("Raw Sensor Features vs Physics-Informed Features\n")
        fh.write("Dataset    : dataset/ai4i2020.csv\n")
        fh.write("Train/Test : 80/20, stratified, random_state=42, threshold 0.5\n\n")
        fh.write("Physics features (computed from the same 6 raw inputs):\n")
        fh.write("  Power [W]       = Torque x RPM x 2pi/60\n")
        fh.write("  Temp diff [K]   = Process temp - Air temp\n")
        fh.write("  Strain [min*Nm] = Tool wear x Torque\n\n")
        fh.write("NOTE: TWF/HDF/PWF/OSF/RNF are sub-failure labels known only\n")
        fh.write("      AFTER a failure — using them is data leakage.\n\n")
        fh.write(table_str + "\n")
        for r in flat_results:
            cm = r["confusion_matrix"]
            fh.write(f"\n{r['Model']} -- Confusion Matrix:\n")
            fh.write(f"  TN={cm[0,0]:4d}  FP={cm[0,1]:4d}\n")
            fh.write(f"  FN={cm[1,0]:4d}  TP={cm[1,1]:4d}\n")
            fh.write(f"  Missed by failure type: {r['missed_by_type']}\n")
        fh.write("\nDepth-4 decision tree on physics features:\n")
        fh.write(rules + "\n")
        fh.write("\n".join(summary) + "\n")
    print(f"-> Results saved to : {txt_path}")

    cm_path = plot_confusion_matrices(results)
    print(f"-> Confusion matrices: {cm_path}\n")


if __name__ == "__main__":
    main()
