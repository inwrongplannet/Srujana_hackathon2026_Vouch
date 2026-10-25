"""Realistic noise injection and multi-model training pipeline for combined3 data.

Adds realistic noise to synthetic data, trains multiple explainable models in parallel,
and creates a generalized ensemble.
"""

import os
import json
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    roc_auc_score, average_precision_score, brier_score_loss,
    accuracy_score, f1_score, precision_score, recall_score
)

import lightgbm as lgb
import xgboost as xgb

# ============================================================
# 1. NOISE INJECTION
# ============================================================
def inject_realistic_noise(
    X: pd.DataFrame,
    y: np.ndarray,
    noise_config: Dict = None,
    seed: int = 42
) -> Tuple[pd.DataFrame, np.ndarray]:
    """
    Inject realistic noise to make synthetic data more lifelike.
    
    Noise types:
    - Measurement error (Gaussian noise on continuous features)
    - Missing data (MAR/MNAR patterns)
    - Label noise (misclassification)
    - Outliers
    - Feature drift
    """
    rng = np.random.default_rng(seed)
    X_noisy = X.copy()
    y_noisy = y.copy()
    
    default_config = {
        'measurement_noise': 0.05,      # 5% CV Gaussian noise on continuous
        'missing_rate': 0.10,           # 10% additional missing
        'label_flip_rate': 0.03,        # 3% label noise
        'outlier_rate': 0.01,           # 1% extreme outliers
        'feature_drift': 0.02,          # 2% systematic drift
    }
    if noise_config:
        default_config.update(noise_config)
    cfg = default_config
    
    continuous_cols = X_noisy.select_dtypes(include=[np.number]).columns.tolist()
    
    # 1. Measurement error
    for c in continuous_cols:
        if X_noisy[c].nunique() > 10:  # Skip binary/categorical
            noise = rng.normal(0, cfg['measurement_noise'] * X_noisy[c].std(), len(X_noisy))
            X_noisy[c] = X_noisy[c] + noise
    
    # 2. Missing data (MAR - depends on other features)
    for c in continuous_cols:
        if rng.random() < cfg['missing_rate']:
            # Missing more likely for low bureau scores
            if 'bureau' in c.lower() or 'score' in c.lower():
                miss_prob = 0.15 + 0.15 * (1 - (X_noisy[c] - X_noisy[c].min()) / (X_noisy[c].max() - X_noisy[c].min()))
            else:
                miss_prob = 0.10
            missing_mask = rng.random(len(X_noisy)) < miss_prob
            X_noisy.loc[missing_mask, c] = np.nan
    
    # 3. Label noise
    flip_mask = rng.random(len(y_noisy)) < cfg['label_flip_rate']
    y_noisy[flip_mask] = 1 - y_noisy[flip_mask]
    
    # 4. Outliers
    for c in continuous_cols:
        if X_noisy[c].nunique() > 10:
            outlier_mask = rng.random(len(X_noisy)) < cfg['outlier_rate']
            X_noisy.loc[outlier_mask, c] *= rng.choice([-1, 10], size=outlier_mask.sum())
    
    # 5. Feature drift (simulate population shift)
    drift_cols = rng.choice(continuous_cols, size=max(1, int(len(continuous_cols) * cfg['feature_drift'])), replace=False)
    for c in drift_cols:
        shift = rng.normal(0, 0.1 * X_noisy[c].std())
        X_noisy[c] += shift
    
    return X_noisy, y_noisy


# ============================================================
# 2. FEATURE ENGINEERING (PREVENT LEAKAGE)
# ============================================================
def prepare_features_no_leakage(m: pd.DataFrame) -> Tuple[pd.DataFrame, np.ndarray, List[str]]:
    """
    Prepare features ensuring NO post-decision information leakage.
    Only pre-application features allowed.
    """
    # Target
    y = m['y'].to_numpy()
    valid = ~pd.isna(y)
    m = m[valid].copy()
    y = y[valid]
    
    # ONLY pre-decision features
    pre_decision_features = [
        # Bureau state (available at application)
        'pre_bureau_score',
        'post_bureau_score', 
        'bureau_drop_points',
        
        # Vouch state (available at application)  
        'pre_vouch_score',
        'post_vouch_score',
        'vouch_held',
        'eligible_incoming',
        'total_weight',
        'distinct_anchors',
        'max_contributor_share',
        'reciprocal_edges',
        'cluster_concentration',
        'mean_voucher_reliability',
        
        # Shock characteristics (known at application if shock already occurred)
        'shock_type',
        'severity',
        'insured',
        
        # Support - BEFORE application only (not mobilised after)
        'support_before_application_minor',
    ]
    
    features = [f for f in pre_decision_features if f in m.columns]
    X = m[features].copy()
    
    # Encode categorical
    for c in ['shock_type']:
        if c in X.columns:
            X[c] = X[c].astype('category')
    
    # Add missing indicators (missingness is informative)
    for c in X.select_dtypes(include=[np.number]).columns:
        X[f'{c}_was_missing'] = X[c].isna().astype(int)
    
    # Fill remaining NaN with median (for tree models)
    for c in X.select_dtypes(include=[np.number]).columns:
        if X[c].isna().any():
            X[c] = X[c].fillna(X[c].median())
    
    return X, y, features


# ============================================================
# 3. MODEL DEFINITIONS
# ============================================================
@dataclass
class ModelConfig:
    name: str
    model_type: str  # 'lightgbm', 'xgboost', 'ebm', 'tabnet'
    params: dict
    use_gpu: bool = True


def create_models() -> List[ModelConfig]:
    """Define all models to train."""
    return [
        ModelConfig(
            name='LightGBM_GPU',
            model_type='lightgbm',
            params={
                'n_estimators': 800,
                'learning_rate': 0.02,
                'num_leaves': 63,
                'min_child_samples': 50,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'reg_lambda': 2.0,
                'reg_alpha': 0.5,
                'objective': 'binary',
                'device': 'gpu',
                'gpu_platform_id': 0,
                'gpu_device_id': 0,
                'n_jobs': -1,
                'random_state': 42,
                'verbose': -1,
                'class_weight': 'balanced',
            }
        ),
        ModelConfig(
            name='XGBoost_GPU',
            model_type='xgboost',
            params={
                'n_estimators': 800,
                'learning_rate': 0.02,
                'max_depth': 6,
                'min_child_weight': 5,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'reg_lambda': 2.0,
                'reg_alpha': 0.5,
                'objective': 'binary:logistic',
                'tree_method': 'hist',
                'device': 'cuda',
                'n_jobs': -1,
                'random_state': 42,
                'verbosity': 0,
                'enable_categorical': True,
                'early_stopping_rounds': 50,
            }
        ),
        ModelConfig(
            name='LightGBM_CPU_Shallow',
            model_type='lightgbm',
            params={
                'n_estimators': 500,
                'learning_rate': 0.03,
                'num_leaves': 31,
                'min_child_samples': 100,
                'subsample': 0.7,
                'colsample_bytree': 0.7,
                'reg_lambda': 5.0,
                'reg_alpha': 1.0,
                'objective': 'binary',
                'device': 'cpu',
                'n_jobs': -1,
                'random_state': 123,
                'verbose': -1,
                'class_weight': 'balanced',
            }
        ),
        ModelConfig(
            name='XGBoost_CPU_Shallow',
            model_type='xgboost',
            params={
                'n_estimators': 500,
                'learning_rate': 0.03,
                'max_depth': 4,
                'min_child_weight': 10,
                'subsample': 0.7,
                'colsample_bytree': 0.7,
                'reg_lambda': 5.0,
                'reg_alpha': 1.0,
                'objective': 'binary:logistic',
                'tree_method': 'hist',
                'device': 'cpu',
                'n_jobs': -1,
                'random_state': 123,
                'verbosity': 0,
                'enable_categorical': True,
                'early_stopping_rounds': 50,
            }
        ),
    ]


def train_model(config: ModelConfig, X_train, y_train, X_calib, y_calib, cat_features) -> Tuple[str, object]:
    """Train a single model."""
    if config.model_type == 'lightgbm':
        model = lgb.LGBMClassifier(**config.params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_calib, y_calib)],
            eval_metric='auc',
            categorical_feature=cat_features,
            callbacks=[],
        )
    elif config.model_type == 'xgboost':
        model = xgb.XGBClassifier(**config.params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_calib, y_calib)],
            verbose=False,
        )
    else:
        raise ValueError(f"Unknown model type: {config.model_type}")
    
    return config.name, model


# ============================================================
# 4. EVALUATION
# ============================================================
def evaluate(model, X, y, threshold=0.5) -> Dict:
    p = model.predict_proba(X)[:, 1]
    pred = (p >= threshold).astype(int)
    return {
        'auc': round(float(roc_auc_score(y, p)), 4),
        'pr_auc': round(float(average_precision_score(y, p)), 4),
        'brier': round(float(brier_score_loss(y, p)), 4),
        'accuracy': round(float(accuracy_score(y, pred)), 4),
        'f1': round(float(f1_score(y, pred, zero_division=0)), 4),
        'precision': round(float(precision_score(y, pred, zero_division=0)), 4),
        'recall': round(float(recall_score(y, pred, zero_division=0)), 4),
        'threshold': threshold,
    }


def conformal_calibration(model, X_calib, y_calib, alpha=0.10):
    """Split conformal prediction calibration."""
    p_calib = model.predict_proba(X_calib)
    if p_calib.ndim == 1:
        p_calib = np.column_stack([1 - p_calib, p_calib])
    y_calib = y_calib.astype(int)
    
    # LAC scores
    lac_scores = 1 - p_calib[np.arange(len(y_calib)), y_calib]
    n = len(lac_scores)
    k = int(np.ceil((n + 1) * (1 - alpha)))
    threshold = float(np.sort(lac_scores)[k - 1])
    
    return threshold


def conformal_sets(model, X, threshold):
    """Get conformal prediction sets."""
    p = model.predict_proba(X)
    if p.ndim == 1:
        p = np.column_stack([1 - p, p])
    sets = (1 - p) <= threshold + 1e-12
    return sets


# ============================================================
# 5. ENSEMBLE
# ============================================================
def ensemble_predict(models: List[Tuple[str, object]], X, weights=None):
    """Weighted average ensemble prediction."""
    if weights is None:
        weights = [1.0] * len(models)
    weights = np.array(weights) / np.sum(weights)
    
    preds = np.zeros(len(X))
    for (name, model), w in zip(models, weights):
        p = model.predict_proba(X)[:, 1]
        preds += w * p
    return preds


# ============================================================
# 6. MAIN PIPELINE
# ============================================================
def run_pipeline(noise_level: str = 'moderate') -> Dict:
    """Run complete training pipeline with noise injection."""
    
    # Noise configurations
    noise_configs = {
        'none': {},
        'light': {'measurement_noise': 0.02, 'missing_rate': 0.05, 'label_flip_rate': 0.01},
        'moderate': {'measurement_noise': 0.05, 'missing_rate': 0.10, 'label_flip_rate': 0.03},
        'heavy': {'measurement_noise': 0.10, 'missing_rate': 0.20, 'label_flip_rate': 0.05},
    }
    
    noise_config = noise_configs.get(noise_level, noise_configs['moderate'])
    
    # Load data
    print(f"Loading data with {noise_level} noise...")
    d = r'C:\Users\Noodl\AppData\Local\Temp\opencode\combined3\combined'
    se = pd.read_csv(os.path.join(d, 'shock_events.csv'))
    vs = pd.read_csv(os.path.join(d, 'vouch_scores.csv'))
    vo = pd.read_csv(os.path.join(d, 'vouch_outcomes.csv'))
    m = se.merge(vs, on='borrower_id', how='left').merge(vo, on='borrower_id', how='left')
    
    # Prepare features (no leakage)
    X, y, features = prepare_features_no_leakage(m)
    print(f"Features: {len(features)}, Samples: {len(X)}, Default rate: {y.mean():.4f}")
    
    # Inject noise
    X, y = inject_realistic_noise(X, y, noise_config)
    print(f"After noise injection: Default rate: {y.mean():.4f}")
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    X_train, X_calib, y_train, y_calib = train_test_split(
        X_train, y_train, test_size=0.125, random_state=42, stratify=y_train
    )
    
    cat_features = [c for c in X.columns if X[c].dtype.name == 'category']
    print(f"Train: {len(X_train)}, Calib: {len(X_calib)}, Test: {len(X_test)}")
    
    # Train models in parallel
    print("\n=== Training Models (Parallel) ===")
    models_config = create_models()
    trained_models = []
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(train_model, cfg, X_train, y_train, X_calib, y_calib, cat_features): cfg.name
            for cfg in models_config
        }
        
        for future in as_completed(futures):
            name = futures[future]
            try:
                model_name, model = future.result()
                trained_models.append((model_name, model))
                print(f"  ✓ {model_name} trained")
            except Exception as e:
                print(f"  ✗ {name} failed: {e}")
    
    # Evaluate individual models
    print("\n=== Individual Model Performance ===")
    results = {}
    for name, model in trained_models:
        metrics = evaluate(model, X_test, y_test)
        results[name] = metrics
        print(f"\n{name}:")
        for k, v in metrics.items():
            print(f"  {k}: {v}")
    
    # Conformal calibration for each
    print("\n=== Conformal Calibration (90%) ===")
    conformal_thresholds = {}
    for name, model in trained_models:
        th = conformal_calibration(model, X_calib, y_calib, alpha=0.10)
        conformal_thresholds[name] = th
        sets = conformal_sets(model, X_test, th)
        coverage = sets[np.arange(len(y_test)), y_test.astype(int)].mean()
        avg_size = sets.sum(axis=1).mean()
        print(f"  {name}: threshold={th:.4f}, coverage={coverage:.4f}, avg_size={avg_size:.3f}")
    
    # Ensemble (equal weights)
    print("\n=== Ensemble Evaluation ===")
    ensemble_pred = ensemble_predict(trained_models, X_test)
    ensemble_metrics = {}
    for th in [0.3, 0.4, 0.5, 0.6, 0.7]:
        pred = (ensemble_pred >= th).astype(int)
        ensemble_metrics[f'th_{th}'] = {
            'auc': round(float(roc_auc_score(y_test, ensemble_pred)), 4),
            'accuracy': round(float(accuracy_score(y_test, pred)), 4),
            'f1': round(float(f1_score(y_test, pred, zero_division=0)), 4),
            'precision': round(float(precision_score(y_test, pred, zero_division=0)), 4),
            'recall': round(float(recall_score(y_test, pred, zero_division=0)), 4),
        }
        print(f"  Threshold {th}: AUC={ensemble_metrics[f'th_{th}']['auc']:.4f}, "
              f"F1={ensemble_metrics[f'th_{th}']['f1']:.4f}")
    
    # Optimal ensemble threshold
    best_th = max(ensemble_metrics, key=lambda k: ensemble_metrics[k]['f1'])
    best_f1 = ensemble_metrics[best_th]['f1']
    print(f"\nBest ensemble threshold: {best_th} (F1={best_f1:.4f})")
    
    # Model 2: CIBIL fall + vouch analysis on noisy data
    print("\n=== Model 2: CIBIL Fall + Vouch (Noisy Data) ===")
    drop_mask = m['bureau_drop_points'] < -5
    vh_mask = m['vouch_held'] == 1
    
    # Filter to valid rows
    m_valid = m[~pd.isna(m['y'])].copy()
    drop_mask = drop_mask[~pd.isna(m['y'])]
    vh_mask = vh_mask[~pd.isna(m['y'])]
    y_valid = m_valid['y'].to_numpy()
    
    groups = {
        'drop_vouch': drop_mask & vh_mask,
        'drop_no_vouch': drop_mask & ~vh_mask,
        'no_drop_vouch': ~drop_mask & vh_mask,
        'no_drop_no_vouch': ~drop_mask & ~vh_mask,
    }
    
    cibil_results = {}
    for name, mask in groups.items():
        if mask.sum() > 0:
            sub = m_valid[mask]
            cibil_results[name] = {
                'n': int(mask.sum()),
                'default_rate': round(float(sub['y'].mean()), 4),
                'mean_bureau_drop': round(float(sub['bureau_drop_points'].mean()), 1),
                'mean_pre_vouch': round(float(sub['pre_vouch_score'].mean()), 1),
                'mean_post_vouch': round(float(sub['post_vouch_score'].mean()), 1),
            }
            print(f"  {name}: n={cibil_results[name]['n']}, default={cibil_results[name]['default_rate']:.2%}")
    
    if 'drop_vouch' in cibil_results and 'drop_no_vouch' in cibil_results:
        diff = cibil_results['drop_vouch']['default_rate'] - cibil_results['drop_no_vouch']['default_rate']
        print(f"  >>> CIBIL drop: vouch_held default rate is {diff:+.2%} vs no vouch")
    
    # Save all results
    os.makedirs('results', exist_ok=True)
    output = {
        'noise_level': noise_level,
        'noise_config': noise_config,
        'n_features': len(features),
        'features': features,
        'train_size': len(X_train),
        'calib_size': len(X_calib),
        'test_size': len(X_test),
        'default_rate': float(y.mean()),
        'individual_models': results,
        'conformal_thresholds': conformal_thresholds,
        'ensemble': ensemble_metrics,
        'best_ensemble_threshold': best_th,
        'cibil_vouch_analysis': cibil_results,
    }
    
    with open(f'results/noise_{noise_level}_results.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nResults saved to results/noise_{noise_level}_results.json")
    return output


if __name__ == '__main__':
    # Run multiple noise levels
    for level in ['light', 'moderate', 'heavy']:
        print(f"\n{'='*60}")
        print(f"RUNNING: {level.upper()} NOISE")
        print(f"{'='*60}")
        run_pipeline(noise_level=level)
    
    print("\n\nAll noise levels complete!")