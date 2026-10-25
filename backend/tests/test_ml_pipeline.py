"""Unit tests for the ML pipeline: realistic noise injection, explainable models, and generalized ensemble."""

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("interpret")

from ml.data import make_shock_splits, Splits
from ml.models import (
    GeneralizedCreditModel,
    LightGBMModel,
    LogisticScorecardModel,
    PyTorchGPUModel,
    XGBoostGPUModel,
)
from ml.noise import NOISE_PRESETS, inject_realistic_noise


def test_noise_injection_clean_preset():
    df = pd.DataFrame({
        "income_minor": [5000000.0, 7500000.0, 3000000.0],
        "bureau_score": [720.0, 650.0, 580.0],
    })
    y = np.array([0, 0, 1])
    X_clean, y_clean, audit = inject_realistic_noise(df, y, NOISE_PRESETS["clean"])

    pd.testing.assert_frame_equal(df, X_clean)
    np.testing.assert_array_equal(y, y_clean)
    assert audit["preset"] == "clean"


def test_noise_injection_realistic_properties():
    rng = np.random.default_rng(42)
    n = 100
    df = pd.DataFrame({
        "income_minor": rng.uniform(2000000, 10000000, size=n),
        "bureau_score": rng.uniform(550, 850, size=n),
        "dti_ratio": rng.uniform(0.1, 0.8, size=n),
    })
    y = rng.choice([0, 1], size=n, p=[0.8, 0.2])

    X_noisy, y_noisy, audit = inject_realistic_noise(df, y, NOISE_PRESETS["realistic"], seed=42)

    assert len(X_noisy) == n
    assert len(y_noisy) == n
    # Monetary fields and non-negative concepts should remain non-negative
    assert (X_noisy["income_minor"].dropna() >= 0).all()
    assert (X_noisy["dti_ratio"].dropna() >= 0).all()
    # Confirm some noise was added
    assert audit["preset"] == "realistic"
    assert audit["continuous_features_perturbed"] > 0


def test_models_and_generalized_ensemble():
    rng = np.random.default_rng(123)
    n_samples = 200
    n_features = 8
    X = pd.DataFrame(
        rng.normal(0, 1, size=(n_samples, n_features)),
        columns=[f"feat_{i}" for i in range(n_features)],
    )
    y = (X["feat_0"] + X["feat_1"] * 0.5 + rng.normal(0, 0.5, size=n_samples) > 0).astype(int).to_numpy()

    # Train / Calib / Test splits
    X_tr, y_tr = X.iloc[:120], y[:120]
    X_ca, y_ca = X.iloc[120:160], y[120:160]
    X_te, y_te = X.iloc[160:], y[160:]

    models = {
        "lgb": LightGBMModel(n_estimators=30).fit(X_tr, y_tr),
        "logistic": LogisticScorecardModel().fit(X_tr, y_tr),
        "xgb": XGBoostGPUModel(n_estimators=30).fit(X_tr, y_tr),
        "pytorch": PyTorchGPUModel(hidden_dim=32, epochs=10).fit(X_tr, y_tr),
    }

    # Verify individual probability outputs
    for name, model in models.items():
        p = model.predict_proba(X_te)
        assert p.shape == (len(X_te), 2)
        assert np.all(p >= 0.0) and np.all(p <= 1.0)
        np.testing.assert_allclose(p.sum(axis=1), 1.0, atol=1e-5)

    # Generalized Ensemble
    ensemble = GeneralizedCreditModel(models)
    p_ens = ensemble.predict_proba(X_te)
    assert p_ens.shape == (len(X_te), 2)
    np.testing.assert_allclose(p_ens.sum(axis=1), 1.0, atol=1e-5)

    # Conformal set outputs
    conformal_res = ensemble.predict_with_conformal(X_te, alpha=0.10)
    assert "conformal_sets" in conformal_res
    assert "decisions" in conformal_res
    assert len(conformal_res["decisions"]) == len(X_te)
    valid_decisions = {"ELIGIBLE", "REVIEW", "DECLINE_CANDIDATE", "ABSTAIN"}
    assert all(d in valid_decisions for d in conformal_res["decisions"])


def test_shock_data_split_integrity():
    splits = make_shock_splits(noise_config="light")
    assert isinstance(splits, Splits)
    assert len(splits.train) > 0
    assert len(splits.calib) > 0
    assert len(splits.test) > 0
    # No post-decision leaks
    assert "support_mobilised_minor" not in splits.features
    assert "default_month" not in splits.features
    assert "_y" in splits.train.columns

