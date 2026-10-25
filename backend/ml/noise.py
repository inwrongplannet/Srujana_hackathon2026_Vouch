"""Realistic synthetic noise injection for credit-risk underwriting and shock evaluation.

Why this exists: Real-world micro-borrower and MSME credit data is noisy. Applicants
round self-declared numbers, bank statements have unobserved cash transactions,
tradelines have reporting delays, and credit outcomes have administrative cures or
technical defaults. Testing models against realistic noise guarantees robustness
and prevents overfitting to synthetic artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class NoiseConfig:
    """Configuration parameters for realistic credit data noise injection."""

    name: str = "realistic"
    measurement_noise: float = 0.05       # 5% relative standard deviation on continuous metrics
    rounding_prob: float = 0.15           # 15% probability of rounding financial amounts (human reporting bias)
    missing_rate: float = 0.08            # 8% additional missingness (MAR / MNAR)
    label_flip_rate: float = 0.025        # 2.5% label noise (administrative cures / technical defaults)
    outlier_rate: float = 0.01            # 1% extreme outlier / black-swan expense shock
    feature_drift: float = 0.02           # 2% macroeconomic shift / drift on features
    preserve_non_negative: bool = True    # Guarantee monetary and count features stay >= 0


NOISE_PRESETS: dict[str, NoiseConfig] = {
    "clean": NoiseConfig(
        name="clean",
        measurement_noise=0.0,
        rounding_prob=0.0,
        missing_rate=0.0,
        label_flip_rate=0.0,
        outlier_rate=0.0,
        feature_drift=0.0,
    ),
    "light": NoiseConfig(
        name="light",
        measurement_noise=0.02,
        rounding_prob=0.08,
        missing_rate=0.04,
        label_flip_rate=0.01,
        outlier_rate=0.005,
        feature_drift=0.01,
    ),
    "realistic": NoiseConfig(
        name="realistic",
        measurement_noise=0.05,
        rounding_prob=0.15,
        missing_rate=0.08,
        label_flip_rate=0.025,
        outlier_rate=0.01,
        feature_drift=0.02,
    ),
    "stressed": NoiseConfig(
        name="stressed",
        measurement_noise=0.10,
        rounding_prob=0.25,
        missing_rate=0.18,
        label_flip_rate=0.05,
        outlier_rate=0.025,
        feature_drift=0.05,
    ),
}


def inject_realistic_noise(
    X: pd.DataFrame,
    y: Optional[np.ndarray] = None,
    config: Optional[NoiseConfig] = None,
    seed: int = 42,
) -> Tuple[pd.DataFrame, Optional[np.ndarray], Dict[str, Any]]:
    """Inject lifelike perturbations into features and labels without target leakage.

    Transforms applied:
    1. Proportional measurement error on continuous metrics (Gaussian jitter).
    2. Heuristic rounding to nearest 1,000 or 10,000 paise on financial fields.
    3. Missing-at-Random (MAR): higher missingness for thin-file or distressed profiles.
    4. Outlier shocks: heavy-tailed perturbations simulating unhedged cash emergencies.
    5. Macro feature drift: slight population-level mean shift.
    6. Label noise: stochastic flips reflecting loan cures or technical delinquencies.
    """
    if config is None:
        config = NOISE_PRESETS["realistic"]

    if config.name == "clean":
        return X.copy(), (y.copy() if y is not None else None), {"preset": "clean", "perturbed_rows": 0}

    rng = np.random.default_rng(seed)
    X_noisy = X.copy()
    y_noisy = y.copy() if y is not None else None
    audit: Dict[str, Any] = {
        "preset": config.name,
        "n_samples": len(X_noisy),
        "continuous_features_perturbed": 0,
        "values_set_missing": 0,
        "labels_flipped": 0,
        "outliers_injected": 0,
    }

    # Identify numeric vs categorical
    numeric_cols = [
        c for c in X_noisy.columns
        if pd.api.types.is_numeric_dtype(X_noisy[c])
        and not c.endswith("_was_missing")
        and not c.startswith("_")
    ]

    # Ensure numeric columns are float64 so they can store float noise and NaNs
    for c in numeric_cols:
        if not pd.api.types.is_float_dtype(X_noisy[c]):
            X_noisy[c] = X_noisy[c].astype(np.float64)

    # 1. Measurement error & rounding on continuous fields
    for c in numeric_cols:
        col_series = X_noisy[c].astype(float)
        non_null_mask = col_series.notna()
        n_valid = int(non_null_mask.sum())
        if n_valid == 0:
            continue

        unique_count = col_series.loc[non_null_mask].nunique()
        # Skip purely binary or small ordinal columns (e.g. 0/1 flags)
        if unique_count <= 4:
            continue

        audit["continuous_features_perturbed"] += 1
        std_val = float(col_series.loc[non_null_mask].std())
        if std_val < 1e-6:
            std_val = 1.0

        # Relative multiplicative jitter: x * (1 + N(0, sigma^2))
        jitter = rng.normal(0, config.measurement_noise, size=n_valid)
        perturbed = col_series.loc[non_null_mask] * (1.0 + jitter)

        # 2. Financial rounding simulation (nearest 1,000 / 5,000 for money columns)
        if "minor" in c or "income" in c or "amount" in c or "turnover" in c:
            round_mask = rng.random(size=n_valid) < config.rounding_prob
            if round_mask.any():
                round_factor = rng.choice([1000.0, 5000.0, 10000.0], size=int(round_mask.sum()))
                perturbed.iloc[round_mask] = np.round(perturbed.iloc[round_mask] / round_factor) * round_factor

        # Respect non-negativity constraint for strictly positive physical concepts
        if config.preserve_non_negative and (col_series.loc[non_null_mask] >= 0).all():
            perturbed = np.maximum(perturbed, 0.0)

        # 3. Outlier injection (extreme shock / unhedged expense)
        if config.outlier_rate > 0:
            outlier_mask = rng.random(size=n_valid) < config.outlier_rate
            if outlier_mask.any():
                scale_multiplier = rng.choice([2.5, 4.0, 0.25], size=int(outlier_mask.sum()))
                perturbed.iloc[outlier_mask] = perturbed.iloc[outlier_mask] * scale_multiplier
                audit["outliers_injected"] += int(outlier_mask.sum())

        X_noisy.loc[non_null_mask, c] = perturbed

    # 4. Realistic Missingness (MAR / MNAR)
    if config.missing_rate > 0:
        for c in numeric_cols:
            non_null = X_noisy[c].notna()
            n_valid = int(non_null.sum())
            if n_valid == 0:
                continue

            # In credit, documentation missingness correlates with thin files
            # or low bureau presence
            base_p = config.missing_rate
            if "bureau" in c.lower() or "gst" in c.lower() or "bank" in c.lower():
                miss_prob = min(0.35, base_p * 1.5)
            else:
                miss_prob = base_p

            drop_mask = rng.random(size=n_valid) < miss_prob
            indices_to_drop = X_noisy.loc[non_null].index[drop_mask]
            X_noisy.loc[indices_to_drop, c] = np.nan
            audit["values_set_missing"] += len(indices_to_drop)

    # 5. Macroeconomic Feature Drift
    if config.feature_drift > 0:
        drift_cols = rng.choice(
            numeric_cols,
            size=max(1, int(len(numeric_cols) * config.feature_drift)),
            replace=False,
        )
        for c in drift_cols:
            col_std = float(X_noisy[c].dropna().std()) if X_noisy[c].notna().any() else 1.0
            shift = rng.normal(0, 0.05 * col_std)
            X_noisy[c] = X_noisy[c] + shift
            if config.preserve_non_negative and (X[c].dropna() >= 0).all():
                X_noisy[c] = np.maximum(X_noisy[c], 0.0)

    # 6. Stochastic Label Noise
    if y_noisy is not None and config.label_flip_rate > 0:
        y_int = y_noisy.astype(int)
        flip_mask = rng.random(size=len(y_int)) < config.label_flip_rate
        y_noisy[flip_mask] = 1 - y_int[flip_mask]
        audit["labels_flipped"] = int(flip_mask.sum())

    return X_noisy, y_noisy, audit
