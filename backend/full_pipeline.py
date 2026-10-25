"""Complete model pipeline: Loan eligibility + CIBIL fall vouch explanation with SHAP explainability."""

import os
import pandas as pd
import numpy as np
import json
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    roc_auc_score, average_precision_score, brier_score_loss, 
    accuracy_score, f1_score, precision_score, recall_score
)

import lightgbm as lgb
import xgboost as xgb
import shap

d = r'C:\Users\Noodl\AppData\Local\Temp\opencode\combined3\combined'

# ============================
# 1. Load and prepare data
# ============================
print("Loading data...")
se = pd.read_csv(os.path.join(d, 'shock_events.csv'))
vs = pd.read_csv(os.path.join(d, 'vouch_scores.csv'))
vo = pd.read_csv(os.path.join(d, 'vouch_outcomes.csv'))

# Merge all tables
m = se.merge(vs, on='borrower_id', how='left').merge(vo, on='borrower_id', how='left')
print(f"Merged rows: {len(m)}")

# Target - drop NaN
y = m['y'].to_numpy()
valid_y = ~pd.isna(y)
m = m[valid_y]
y = y[valid_y]
print(f"After dropping NaN target: {len(m)} rows")

# ============================
# 2. Feature engineering with MISSING AS INFORMATIVE
# ============================
# Key features - missing values kept as NaN (LightGBM/XGBoost handle natively)
# We also add missing indicators for interpretability
features = [
    'pre_bureau_score',      # Bureau score before shock
    'post_bureau_score',     # Bureau score after shock
    'bureau_drop_points',    # Points dropped (negative = drop)
    'pre_vouch_score',       # Vouch score before
    'post_vouch_score',      # Vouch score after
    'vouch_held',            # Binary: vouch score maintained through shock
    'shock_type',            # MEDICAL, JOB_LOSS, FAMILY, BUSINESS_DISRUPTION, CROP
    'severity',              # 1, 2, 3
    'insured',               # Binary
    'support_mobilised_minor',        # Community support mobilised
    'support_before_application_minor', # Support before applying
    'eligible_incoming',     # Number of incoming vouches
    'total_weight',          # Total vouch weight
    'distinct_anchors',      # Distinct anchor nodes
    'max_contributor_share', # Concentration risk
    'reciprocal_edges',      # Reciprocal vouching
    'cluster_concentration', # Cluster concentration
    'mean_voucher_reliability', # Voucher quality
    # Post-outcome features EXCLUDED (leakage): loan_status, p_expected, edge_weight, delta_reputation
]

# Only keep features that exist
features = [f for f in features if f in m.columns]

# Encode categorical as codes (LightGBM handles category dtype)
X = m[features].copy()
for c in ['shock_type', 'loan_status']:
    if c in X.columns:
        X[c] = X[c].astype('category')

# Add missing indicators for key financial fields (missing = important signal)
for c in ['pre_bureau_score', 'post_bureau_score', 'bureau_drop_points',
          'pre_vouch_score', 'post_vouch_score', 'p_expected']:
    if c in X.columns:
        X[f'{c}_missing'] = X[c].isna().astype(int)

# Split - stratify by target
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# Also create a holdout for calibration (conformal prediction)
X_train, X_calib, y_train, y_calib = train_test_split(
    X_train, y_train, test_size=0.125, random_state=42, stratify=y_train
)

print(f"Train: {len(X_train)}, Calib: {len(X_calib)}, Test: {len(X_test)}")

# ============================
# 3. Train LightGBM (GPU)
# ============================
print("\n=== Training LightGBM (GPU) ===")
lgb_model = lgb.LGBMClassifier(
    n_estimators=500,
    learning_rate=0.03,
    num_leaves=63,
    min_child_samples=30,
    subsample=0.8,
    subsample_freq=1,
    colsample_bytree=0.8,
    reg_lambda=1.0,
    reg_alpha=0.1,
    objective='binary',
    device='gpu',
    gpu_platform_id=0,
    gpu_device_id=0,
    n_jobs=-1,
    random_state=42,
    verbose=-1,
    class_weight='balanced',
)

lgb_model.fit(
    X_train, y_train,
    eval_set=[(X_calib, y_calib)],
    eval_metric='auc',
    categorical_feature=[c for c in X.columns if X[c].dtype.name == 'category'],
)

# ============================
# 4. Train XGBoost (GPU)
# ============================
print("\n=== Training XGBoost (GPU) ===")
xgb_model = xgb.XGBClassifier(
    n_estimators=500,
    learning_rate=0.03,
    max_depth=6,
    min_child_weight=3,
    subsample=0.8,
    colsample_bytree=0.8,
    reg_lambda=1.0,
    reg_alpha=0.1,
    objective='binary:logistic',
    tree_method='hist',
    device='cuda',
    n_jobs=-1,
    random_state=42,
    verbosity=0,
    enable_categorical=True,
    early_stopping_rounds=50,
)

xgb_model.fit(
    X_train, y_train,
    eval_set=[(X_calib, y_calib)],
    verbose=False,
)

# ============================
# 5. Evaluate both models
# ============================
def evaluate_model(model, X, y, name):
    p = model.predict_proba(X)[:, 1]
    th = 0.5
    pred = (p >= th).astype(int)
    return {
        'model': name,
        'n': int(len(y)),
        'auc': round(float(roc_auc_score(y, p)), 4),
        'pr_auc': round(float(average_precision_score(y, p)), 4),
        'brier': round(float(brier_score_loss(y, p)), 4),
        'accuracy': round(float(accuracy_score(y, pred)), 4),
        'f1': round(float(f1_score(y, pred, zero_division=0)), 4),
        'precision': round(float(precision_score(y, pred, zero_division=0)), 4),
        'recall': round(float(recall_score(y, pred, zero_division=0)), 4),
        'threshold': th,
    }

lgb_metrics = evaluate_model(lgb_model, X_test, y_test, 'LightGBM')
xgb_metrics = evaluate_model(xgb_model, X_test, y_test, 'XGBoost')

print("\n=== Test Metrics ===")
for m in [lgb_metrics, xgb_metrics]:
    print(f"\n{m['model']}:")
    for k, v in m.items():
        if k != 'model':
            print(f"  {k}: {v}")

# ============================
# 6. SHAP Explainability
# ============================
print("\n=== Computing SHAP values ===")
# Use a sample for SHAP (computationally expensive)
sample_size = min(2000, len(X_test))
X_shap = X_test.sample(sample_size, random_state=42)

# LightGBM SHAP
explainer_lgb = shap.TreeExplainer(lgb_model)
shap_values_lgb = explainer_lgb.shap_values(X_shap)
if isinstance(shap_values_lgb, list):
    shap_values_lgb = shap_values_lgb[1]  # positive class

# XGBoost SHAP
explainer_xgb = shap.TreeExplainer(xgb_model)
shap_values_xgb = explainer_xgb.shap_values(X_shap)

# Feature importance (mean |SHAP|)
def get_shap_importance(shap_vals, feature_names):
    mean_abs = np.abs(shap_vals).mean(axis=0)
    return pd.DataFrame({
        'feature': feature_names,
        'mean_abs_shap': mean_abs
    }).sort_values('mean_abs_shap', ascending=False)

lgb_shap_imp = get_shap_importance(shap_values_lgb, X_shap.columns.tolist())
xgb_shap_imp = get_shap_importance(shap_values_xgb, X_shap.columns.tolist())

print("\n=== Top 15 Features by SHAP (LightGBM) ===")
for _, row in lgb_shap_imp.head(15).iterrows():
    print(f"  {row['feature']}: {row['mean_abs_shap']:.4f}")

# ============================
# 7. Conformal Prediction (90% coverage)
# ============================
print("\n=== Conformal Prediction (LightGBM) ===")
p_calib = lgb_model.predict_proba(X_calib)
# Ensure 2D (n_samples, n_classes)
if p_calib.ndim == 1:
    p_calib = np.column_stack([1 - p_calib, p_calib])
y_calib_int = y_calib.astype(int)

# LAC scores
lac_scores = 1 - p_calib[np.arange(len(y_calib_int)), y_calib_int]
alpha = 0.10
n = len(lac_scores)
k = int(np.ceil((n + 1) * (1 - alpha)))
threshold = float(np.sort(lac_scores)[k - 1])
print(f"Conformal threshold: {threshold:.4f}")

# Apply to test
p_test = lgb_model.predict_proba(X_test)
if p_test.ndim == 1:
    p_test = np.column_stack([1 - p_test, p_test])
y_test_int = y_test.astype(int)
sets = (1 - p_test) <= threshold + 1e-12
coverage = sets[np.arange(len(y_test_int)), y_test_int].mean()
avg_size = sets.sum(axis=1).mean()
print(f"Test coverage: {coverage:.4f} (target: {1-alpha:.2f})")
print(f"Avg set size: {avg_size:.3f}")
print(f"Singleton rate: {(sets.sum(axis=1)==1).mean():.3f}")
print(f"Empty rate: {(sets.sum(axis=1)==0).mean():.3f}")

# ============================
# 8. Model 2: CIBIL Fall + Vouch Explanation
# ============================
print("\n=== Model 2: CIBIL Fall + Vouch Held ===")
# Use original merged data before train/test split
se = pd.read_csv(os.path.join(d, 'shock_events.csv'))
vs = pd.read_csv(os.path.join(d, 'vouch_scores.csv'))
vo = pd.read_csv(os.path.join(d, 'vouch_outcomes.csv'))
m2 = se.merge(vs, on='borrower_id', how='left').merge(vo, on='borrower_id', how='left')
y2 = m2['y'].to_numpy()
valid2 = ~pd.isna(y2)
m2 = m2[valid2]
y2 = y2[valid2]

drop_mask = m2['bureau_drop_points'] < -5  # Significant drop
vh_mask = m2['vouch_held'] == 1

# Four groups
groups = {
    'drop_vouch': drop_mask & vh_mask,
    'drop_no_vouch': drop_mask & ~vh_mask,
    'no_drop_vouch': ~drop_mask & vh_mask,
    'no_drop_no_vouch': ~drop_mask & ~vh_mask,
}

results_cibil = {}
for name, mask in groups.items():
    sub = m2[mask]
    if len(sub) > 0:
        results_cibil[name] = {
            'n': int(len(sub)),
            'default_rate': round(float(sub['y'].mean()), 4),
            'mean_bureau_drop': round(float(sub['bureau_drop_points'].mean()), 1) if 'bureau_drop_points' in sub.columns else None,
            'mean_pre_vouch': round(float(sub['pre_vouch_score'].mean()), 1) if 'pre_vouch_score' in sub.columns else None,
            'mean_post_vouch': round(float(sub['post_vouch_score'].mean()), 1) if 'post_vouch_score' in sub.columns else None,
            'mean_pre_bureau': round(float(sub['pre_bureau_score'].mean()), 1) if 'pre_bureau_score' in sub.columns else None,
            'mean_post_bureau': round(float(sub['post_bureau_score'].mean()), 1) if 'post_bureau_score' in sub.columns else None,
        }

print("\n=== CIBIL Fall + Vouch Analysis ===")
for name, res in results_cibil.items():
    print(f"\n{name}: n={res['n']}, default={res['default_rate']:.2%}")
    for k, v in res.items():
        if k != 'n' and k != 'default_rate' and v is not None:
            print(f"  {k}: {v}")

# Key comparison
if 'drop_vouch' in results_cibil and 'drop_no_vouch' in results_cibil:
    diff = results_cibil['drop_vouch']['default_rate'] - results_cibil['drop_no_vouch']['default_rate']
    print(f"\n>>> With CIBIL drop: vouch_held default rate is {diff:+.2%} vs no vouch")

# ============================
# 9. Per-instance explanations
# ============================
print("\n=== Sample Explanations (LightGBM SHAP) ===")
# Get 3 examples: approved, borderline, rejected
p_test_lgb = lgb_model.predict_proba(X_test)[:, 1]
order = np.argsort(p_test_lgb)

# Map test indices to SHAP sample indices
X_shap_indices = X_shap.index.tolist()

cases = {
    'lowest_risk (approved)': order[0],
    'borderline': order[len(order)//2],
    'highest_risk (rejected)': order[-1],
}

for case_name, idx in cases.items():
    borrower_id = X_test.index[idx]
    row = X_test.iloc[[idx]]
    true_label = y_test[idx]
    pred_prob = p_test_lgb[idx]
    
    # Find this row in SHAP sample
    try:
        shap_idx = X_shap_indices.index(borrower_id)
        shap_row = shap_values_lgb[shap_idx]
    except (ValueError, IndexError):
        # Compute SHAP for this specific row
        shap_row = explainer_lgb.shap_values(row)[0][0]
    
    # Top positive/negative contributors
    contrib = pd.DataFrame({
        'feature': row.columns,
        'value': row.iloc[0].values,
        'shap': shap_row
    }).sort_values('shap', key=abs, ascending=False)
    
    print(f"\n--- {case_name} (borrower {borrower_id}) ---")
    print(f"  True: {int(true_label)}, Predicted prob: {pred_prob:.3f}")
    print(f"  Conformal set: repay={sets[idx,0]}, default={sets[idx,1]}")
    
    print("  Top risk-increasing factors (SHAP > 0):")
    for _, r in contrib[contrib['shap'] > 0].head(5).iterrows():
        print(f"    + {r['feature']}: {r['value']} -> SHAP={r['shap']:.3f}")
    
    print("  Top protective factors (SHAP < 0):")
    for _, r in contrib[contrib['shap'] < 0].head(5).iterrows():
        print(f"    - {r['feature']}: {r['value']} -> SHAP={r['shap']:.3f}")

# ============================
# 10. Save all results
# ============================
os.makedirs('results', exist_ok=True)

all_results = {
    'metrics': {
        'lightgbm': lgb_metrics,
        'xgboost': xgb_metrics,
        'conformal': {
            'threshold': round(threshold, 4),
            'target_coverage': 1 - alpha,
            'achieved_coverage': round(float(coverage), 4),
            'avg_set_size': round(float(avg_size), 3),
        }
    },
    'shap_importance': {
        'lightgbm': lgb_shap_imp.head(20).to_dict('records'),
        'xgboost': xgb_shap_imp.head(20).to_dict('records'),
    },
    'cibil_vouch_analysis': results_cibil,
    'feature_list': features,
    'n_train': len(X_train),
    'n_calib': len(X_calib),
    'n_test': len(X_test),
}

with open('results/full_pipeline_results.json', 'w') as f:
    json.dump(all_results, f, indent=2)

print("\n=== All results saved to results/full_pipeline_results.json ===")
print("\nDone!")