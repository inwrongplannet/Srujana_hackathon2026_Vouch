"""Dataset loading and feature preparation for the combined credit dataset.

Why this exists: one place that knows which columns are model inputs, which are
labels, and which would leak the answer or the data source. Every model script
imports from here so the splits are identical.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, Union

import numpy as np
import pandas as pd

from .noise import NoiseConfig, NOISE_PRESETS, inject_realistic_noise

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "combined")

# Never a feature: identifiers, labels, the hidden answer key, and derived
# vendor decisions (legacy_decision is a rule over bureau fields, so learning it
# would be circular).
ALWAYS_DROP = {
    "source",
    "borrower_id",
    "recommended_use",
    "legacy_decision",
    "legacy_reason",
    "application_month",
    # labels and post-outcome fields
    "default_12m",
    "default_month",
    "max_dpd_12m",
    "cure_month",
    "support_mobilised_minor",  # mobilized AFTER application
}

# Present in one source only, or constant within a source. Including them lets a
# model learn "which dataset am I" instead of "will this person repay".
SOURCE_ONLY = {
    # real_anchored only
    "occupation_type",
    "owns_realty",
    "region_rating",
    "bureau_enquiries_12m",
    "bureau_current_overdue_max",
    "hc_prev_applications",
    "hc_prev_refused",
    "hc_instalments_12m",
    "hc_late_share_12m",
    "hc_short_share_12m",
    "hc_max_days_late_12m",
    "hc_late_share_all",
    "hc_history_status",
    # simulated only
    "vouch_count",
    "vouch_mean_voucher_on_time",
    "vouch_status",
    # absent or constant by construction
    "state",
    "rate_annual",
}

CATEGORICAL = [
    "occupation",
    "product",
    "age_band",
    "bank_statement_status",
    "bureau_status",
    "gst_status",
    "declared_income_status",
    "occupation_tenure_status",
    "income_basis",
    "completeness_tier",
    "shock_type",
    "severity",
]

# Columns that are money in minor units; kept as int until model input.
MONEY_COLUMNS = [c for c in ["requested_amount_minor", "new_emi_minor",
                             "declared_income_minor", "declared_emi_minor"]]


@dataclass
class Splits:
    """Train / calibration / test frames with the label and borrower id."""

    train: pd.DataFrame
    calib: pd.DataFrame
    test: pd.DataFrame
    features: list[str]
    categorical: list[str]
    noise_audit: Optional[dict] = None


def load_raw(data_dir: str = DATA_DIR) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (features, label) aligned on borrower_id."""
    feats = pd.read_csv(os.path.join(data_dir, "features.csv"), low_memory=False)
    outcomes = pd.read_csv(os.path.join(data_dir, "outcomes.csv"), low_memory=False)
    label = outcomes.set_index("borrower_id")[["default_12m", "default_month", "max_dpd_12m"]]
    feats = feats.set_index("borrower_id")
    label = label.reindex(feats.index)
    return feats, label


def feature_columns(feats: pd.DataFrame) -> list[str]:
    """Columns usable as model input, derived from the data, not hand-listed."""
    drop = ALWAYS_DROP | SOURCE_ONLY
    keep = [c for c in feats.columns if c not in drop and feats[c].notna().any()]
    # A column that is empty for one source is a source flag, not a feature.
    for c in keep[:]:
        by_source = feats.groupby("source")[c].apply(lambda s: s.notna().mean())
        if (by_source < 0.001).any():
            keep.remove(c)
    return keep


def build_matrix(feats: pd.DataFrame, cols: list[str], categories: dict[str, list]) -> pd.DataFrame:
    """Encode categoricals as integer codes; leave NaN as NaN so models see missingness."""
    X = pd.DataFrame(index=feats.index)
    for c in cols:
        if c in CATEGORICAL:
            cats = categories.get(c, [])
            mapping = {v: i for i, v in enumerate(cats)}
            # -1 is its own "missing" category; no imputation of the real value.
            X[c] = feats[c].map(mapping).fillna(-1).astype("float64")
        else:
            X[c] = pd.to_numeric(feats[c], errors="coerce").astype("float64")
    return X


def make_splits(
    data_dir: str = DATA_DIR,
    seed: int = 42,
    calib_frac: float = 0.20,
    source: str = "real_anchored",
    extra_columns: tuple[str, ...] = (),
    noise_config: Optional[Union[NoiseConfig, str]] = None,
) -> Splits:
    """Stratified split by borrower. Conformal validity needs exchangeability,
    so this is a random split, not a time split; train.py also reports a
    time holdout as a robustness check.
    """
    feats, label = load_raw(data_dir)
    feats = feats.join(label)
    feats = feats[feats["source"] == source]

    cols = feature_columns(feats) + [c for c in extra_columns if c not in feature_columns(feats)]
    categories = {
        c: sorted(feats[c].dropna().unique().tolist()) for c in cols if c in CATEGORICAL
    }

    rng = np.random.default_rng(seed)
    idx = feats.index.to_numpy()
    y = feats["default_12m"].to_numpy()
    pos = idx[y == 1]
    neg = idx[y == 0]
    rng.shuffle(pos)
    rng.shuffle(neg)

    # Stratified 60/20/20 per class; class order fixed so the split is reproducible.
    n_pos_test = int(len(pos) * calib_frac)
    n_pos_calib = int(len(pos) * calib_frac)
    n_neg_test = int(len(neg) * calib_frac)
    n_neg_calib = int(len(neg) * calib_frac)

    test_ids = np.concatenate([pos[:n_pos_test], neg[:n_neg_test]])
    calib_ids = np.concatenate([pos[n_pos_test:n_pos_test + n_pos_calib],
                                neg[n_neg_test:n_neg_test + n_neg_calib]])
    train_ids = np.concatenate([pos[n_pos_test + n_pos_calib:],
                                neg[n_neg_test + n_neg_calib:]])

    X = build_matrix(feats, cols, categories)

    # Optional noise injection for training data
    audit = None
    if noise_config is not None:
        cfg = NOISE_PRESETS[noise_config] if isinstance(noise_config, str) else noise_config
        X_train_noisy, y_train_noisy, audit = inject_realistic_noise(
            X.loc[train_ids], feats.loc[train_ids, "default_12m"].to_numpy(), cfg, seed=seed
        )
        X.loc[train_ids] = X_train_noisy
        feats.loc[train_ids, "default_12m"] = y_train_noisy

    parts = {}
    for name, ids in (("train", train_ids), ("calib", calib_ids), ("test", test_ids)):
        sub = X.loc[ids].copy()
        sub["_y"] = feats.loc[ids, "default_12m"].to_numpy()
        sub["_tier"] = feats.loc[ids, "completeness_tier"].astype(str).to_numpy() if "completeness_tier" in feats.columns else "TIER_2"
        sub["_id"] = ids
        parts[name] = sub

    return Splits(parts["train"], parts["calib"], parts["test"], cols, CATEGORICAL, noise_audit=audit)


def split_xy(df: pd.DataFrame, features: list[str]) -> tuple[pd.DataFrame, np.ndarray]:
    return df[features], df["_y"].to_numpy().astype(int)


# --------------------------------------------------------------------------- #
# Vouch Shock Dataset Loading (Option A Spec)
# --------------------------------------------------------------------------- #
def load_shock_data(data_dir: str = DATA_DIR) -> tuple[pd.DataFrame, np.ndarray, list[str]]:
    """Load combined shock events, vouch scores, and settled vouch repayment outcomes.

    Strictly drops any post-decision information (preventing target leakage).
    """
    se_path = os.path.join(data_dir, "shock_events.csv")
    vs_path = os.path.join(data_dir, "vouch_scores.csv")
    vo_path = os.path.join(data_dir, "vouch_outcomes.csv")

    if not (os.path.exists(se_path) and os.path.exists(vs_path) and os.path.exists(vo_path)):
        raise FileNotFoundError(f"Shock data files missing in {data_dir}")

    se = pd.read_csv(se_path, low_memory=False)
    vs = pd.read_csv(vs_path, low_memory=False).drop_duplicates(subset=["borrower_id"])
    vo = pd.read_csv(vo_path, low_memory=False).dropna(subset=["y"]).drop_duplicates(subset=["borrower_id"])

    # Merge shock events, vouch metrics, and outcomes
    m = se.merge(vs, on="borrower_id", how="left").merge(vo, on="borrower_id", how="inner")

    # Strictly pre-decision features available at underwriting time
    pre_decision_features = [
        # Bureau trajectory features
        "pre_bureau_score",
        "post_bureau_score",
        "bureau_drop_points",
        "bureau_shock",
        # Vouch network metrics
        "pre_vouch_score",
        "post_vouch_score",
        "vouch_held",
        "eligible_incoming",
        "total_weight",
        "distinct_anchors",
        "max_contributor_share",
        "reciprocal_edges",
        "cluster_concentration",
        "mean_voucher_reliability",
        # Shock context
        "shock_type",
        "severity",
        "insured",
        "support_before_application_minor",
    ]

    features = [f for f in pre_decision_features if f in m.columns]
    X = m.set_index("borrower_id")[features].copy()
    y = m.set_index("borrower_id")["y"].to_numpy().astype(int)

    # Ensure all feature columns in X are float64 to support missingness and float perturbations
    for c in features:
        X[c] = pd.to_numeric(X[c], errors="coerce").astype(float)

    # Encode categoricals
    for c in ["shock_type", "severity"]:
        if c in X.columns:
            cats = sorted(X[c].dropna().unique().tolist())
            mapping = {v: i for i, v in enumerate(cats)}
            X[c] = X[c].map(mapping).fillna(-1).astype(float)

    # Informative missingness flags
    for c in features[:]:
        if X[c].isna().any():
            flag_name = f"{c}_was_missing"
            X[flag_name] = X[c].isna().astype(float)
            if flag_name not in features:
                features.append(flag_name)

    return X, y, features


def make_shock_splits(
    data_dir: str = DATA_DIR,
    seed: int = 42,
    calib_frac: float = 0.20,
    noise_config: Optional[Union[NoiseConfig, str]] = None,
) -> Splits:
    """Generate stratified train/calibration/test splits for the Vouch Shock Dataset."""
    X, y, features = load_shock_data(data_dir)

    rng = np.random.default_rng(seed)
    idx = X.index.to_numpy()
    pos = idx[y == 1]
    neg = idx[y == 0]
    rng.shuffle(pos)
    rng.shuffle(neg)

    n_pos_test = int(len(pos) * calib_frac)
    n_pos_calib = int(len(pos) * calib_frac)
    n_neg_test = int(len(neg) * calib_frac)
    n_neg_calib = int(len(neg) * calib_frac)

    test_ids = np.concatenate([pos[:n_pos_test], neg[:n_neg_test]])
    calib_ids = np.concatenate([pos[n_pos_test:n_pos_test + n_pos_calib],
                                neg[n_neg_test:n_neg_test + n_neg_calib]])
    train_ids = np.concatenate([pos[n_pos_test + n_pos_calib:],
                                neg[n_neg_test + n_neg_calib:]])

    audit = None
    y_series = pd.Series(y, index=idx)
    if noise_config is not None:
        cfg = NOISE_PRESETS[noise_config] if isinstance(noise_config, str) else noise_config
        X_tr_noisy, y_tr_noisy, audit = inject_realistic_noise(
            X.loc[train_ids], y_series.loc[train_ids].to_numpy(), cfg, seed=seed
        )
        X.loc[train_ids] = X_tr_noisy
        y_series.loc[train_ids] = y_tr_noisy

    parts = {}
    for name, ids in (("train", train_ids), ("calib", calib_ids), ("test", test_ids)):
        sub = X.loc[ids].copy()
        sub["_y"] = y_series.loc[ids].to_numpy()
        sub["_tier"] = "SHOCK_BORROWER"
        sub["_id"] = ids
        parts[name] = sub

    return Splits(parts["train"], parts["calib"], parts["test"], features, ["shock_type", "severity"], noise_audit=audit)
