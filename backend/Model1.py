"""Model 1: Loan eligibility prediction on combined3 data."""

import os
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, accuracy_score, f1_score
from sklearn.model_selection import train_test_split

d = r'C:\Users\Noodl\AppData\Local\Temp\opencode\combined3\combined'

# Load and merge key tables
se = pd.read_csv(os.path.join(d, 'shock_events.csv'))
vs = pd.read_csv(os.path.join(d, 'vouch_scores.csv'))
vo = pd.read_csv(os.path.join(d, 'vouch_outcomes.csv'))
m = se.merge(vs, on='borrower_id', how='left').merge(vo, on='borrower_id', how='left')

features = [
    'pre_bureau_score', 'post_bureau_score', 'bureau_drop_points',
    'pre_vouch_score', 'post_vouch_score', 'vouch_held',
    'shock_type', 'severity', 'insured',
    'support_mobilised_minor', 'support_before_application_minor',
]

X = m[features].copy()
y = m['y'].to_numpy()
# Drop rows where y is NaN
valid = ~pd.isna(y)
X = X[valid]
y = y[valid]

# Handle missing values
for c in features:
    if X[c].isna().any():
        X[c] = X[c].fillna(X[c].median())

# Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y)

# LightGBM
from lightgbm import LGBMClassifier
lgb = LGBMClassifier(n_estimators=200, learning_rate=0.05, num_leaves=31,
                     min_child_samples=20, subsample=0.8, colsample_bytree=0.8,
                     reg_lambda=1.0, objective='binary', n_jobs=-1, random_state=42)
lgb.fit(X_train.fillna(0), y_train)

p = lgb.predict_proba(X_test.fillna(0))[:, 1]
th = 0.5

metrics = {
    'auc': round(float(roc_auc_score(y_test, p)), 4),
    'pr_auc': round(float(average_precision_score(y_test, p)), 4),
    'brier': round(float(brier_score_loss(y_test, p)), 4),
    'accuracy': round(float(accuracy_score(y_test, (p >= th).astype(int))), 4),
    'f1': round(float(f1_score(y_test, (p >= th).astype(int), zero_division=0)), 4),
    'threshold': round(th, 4),
}

print('=== Model 1: Loan eligibility prediction ===')
for k, v in metrics.items():
    print(f'  {k}: {v}')

# Feature importance
imp = lgb.feature_importances_
feat_imp = sorted(zip(features, imp), key=lambda x: x[1], reverse=True)
print('\nTop features:')
for f, v in feat_imp[:15]:
    print(f'  {f}: {v:.4f}')

# Save metrics
import json
with open('results/model1_metrics.json', 'w') as f:
    json.dump(metrics, f, indent=2)
print('\nMetrics saved to results/model1_metrics.json')
PYEOF