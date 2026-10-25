"""Train, calibrate and evaluate explainable credit-default models with conformal sets.

Includes:
- Realistic synthetic noise injection (measurement jitter, rounding, MAR missingness, label noise).
- Parallel GPU-accelerated training on NVIDIA GeForce RTX 4050 Laptop GPU (PyTorch GPU, XGBoost GPU).
- Glassbox Explainable Boosting Machine (EBM) and depth-regularized LightGBM.
- GeneralizedCreditModel meta-ensemble with finite-sample Conformal Prediction set coverage.
- Option A Market-Shock vouch evaluation (testing whether vouch score compensates for CIBIL score drops).

Run from `backend/`:
    .venv/Scripts/python.exe -m ml.train          # Windows
    .venv/bin/python -m ml.train                  # POSIX
"""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    f1_score,
    log_loss,
    roc_auc_score,
    roc_curve,
)

from . import conformal, data, explain
from .models import (
    EBMModel,
    GeneralizedCreditModel,
    LightGBMModel,
    LogisticScorecardModel,
    PyTorchGPUModel,
    XGBoostGPUModel,
    CUDA_AVAILABLE,
)
from .noise import NOISE_PRESETS, NoiseConfig

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
MODELS_DIR = os.path.join(RESULTS_DIR, "models")


# --------------------------------------------------------------------------- #
# Metrics & Thresholds
# --------------------------------------------------------------------------- #
def ks_statistic(y: np.ndarray, p: np.ndarray) -> float:
    fpr, tpr, _ = roc_curve(y, p)
    return float(np.max(tpr - fpr))


def best_threshold(y: np.ndarray, p: np.ndarray) -> float:
    """Threshold maximising F1 on the calibration split; used for accuracy only."""
    grid = np.linspace(0.02, 0.9, 177)
    scores = [f1_score(y, (p >= t).astype(int), zero_division=0) for t in grid]
    return float(grid[int(np.argmax(scores))])


def evaluate(y: np.ndarray, p: np.ndarray, threshold: float = 0.5) -> dict:
    pred = (p >= threshold).astype(int)
    return {
        "n": int(len(y)),
        "positives": int(y.sum()),
        "auc": round(float(roc_auc_score(y, p)), 4),
        "pr_auc": round(float(average_precision_score(y, p)), 4),
        "brier": round(float(brier_score_loss(y, p)), 4),
        "log_loss": round(float(log_loss(y, np.clip(p, 1e-6, 1.0 - 1e-6))), 4),
        "ks": round(ks_statistic(y, p), 4),
        "accuracy_at_threshold": round(float(accuracy_score(y, pred)), 4),
        "balanced_accuracy": round(float(balanced_accuracy_score(y, pred)), 4),
        "f1": round(float(f1_score(y, pred, zero_division=0)), 4),
        "precision": round(float(((pred == 1) & (y == 1)).sum() / max(pred.sum(), 1)), 4),
        "recall": round(float(((pred == 1) & (y == 1)).sum() / max(y.sum(), 1)), 4),
        "approval_rate": round(float((pred == 0).mean()), 4),
        "threshold": round(threshold, 4),
    }


def bootstrap_diff(a: np.ndarray, b: np.ndarray, n_boot: int = 1500, seed: int = 7) -> dict:
    """Bootstrap CI for mean(a) - mean(b) on binary outcomes."""
    if len(a) == 0 or len(b) == 0:
        return {"diff": None, "ci_low": None, "ci_high": None}
    rng = np.random.default_rng(seed)
    point = float(a.mean() - b.mean())
    draws = []
    for _ in range(n_boot):
        draws.append(rng.choice(a).mean() - rng.choice(b).mean())
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return {"diff": round(point, 4), "ci_low": round(float(lo), 4), "ci_high": round(float(hi), 4)}


def bootstrap_auc_diff(y: np.ndarray, p_a: np.ndarray, p_b: np.ndarray, n_boot: int = 400, seed: int = 7) -> dict:
    rng = np.random.default_rng(seed)
    point = roc_auc_score(y, p_a) - roc_auc_score(y, p_b)
    idx = np.arange(len(y))
    draws = []
    for _ in range(n_boot):
        s = rng.choice(idx, size=len(idx), replace=True)
        if y[s].sum() == 0 or y[s].sum() == len(s):
            continue
        draws.append(roc_auc_score(y[s], p_a[s]) - roc_auc_score(y[s], p_b[s]))
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return {
        "delta_auc": round(float(point), 4),
        "ci_low": round(float(lo), 4),
        "ci_high": round(float(hi), 4),
        "significant": bool(lo > 0 or hi < 0),
    }


# --------------------------------------------------------------------------- #
# Parallel Training of Individual Model Candidate
# --------------------------------------------------------------------------- #
def _train_single_model(
    name: str,
    X_fit: pd.DataFrame,
    y_fit: np.ndarray,
    X_va: pd.DataFrame,
    y_va: np.ndarray,
    X_full_tr: pd.DataFrame,
    y_full_tr: np.ndarray,
    categorical: list[str],
) -> Tuple[str, Any]:
    """Train a single model candidate (dispatched in threadpool across GPU/CPU)."""
    if name == "xgboost_gpu":
        m = XGBoostGPUModel(n_estimators=600, learning_rate=0.03, use_gpu=CUDA_AVAILABLE)
        m.fit(X_fit, y_fit, X_va, y_va)
        return name, m

    elif name == "pytorch_gpu":
        m = PyTorchGPUModel(hidden_dim=128, lr=0.001, epochs=35, dropout=0.2)
        m.fit(X_fit, y_fit, X_va, y_va)
        return name, m

    elif name == "ebm":
        m = EBMModel(interactions=0, max_bins=256)
        m.fit(X_full_tr, y_full_tr, categorical=categorical)
        return name, m

    elif name == "lightgbm":
        m = LightGBMModel(n_estimators=800, learning_rate=0.02)
        m.fit(X_fit, y_fit, X_va, y_va, categorical=categorical)
        return name, m

    elif name == "logistic":
        m = LogisticScorecardModel(C=1.0)
        m.fit(X_full_tr, y_full_tr)
        return name, m

    raise ValueError(f"Unknown model name {name}")


# --------------------------------------------------------------------------- #
# Pipeline Execution for Standard Underwriting Splits
# --------------------------------------------------------------------------- #
def run_source(
    source: str,
    extra_columns: tuple[str, ...] = (),
    noise_level: str = "realistic",
) -> dict:
    """Train explainable models in parallel on one source with noise injection."""
    splits = data.make_splits(source=source, extra_columns=extra_columns, noise_config=noise_level)
    X_tr, y_tr = data.split_xy(splits.train, splits.features)
    X_ca, y_ca = data.split_xy(splits.calib, splits.features)
    X_te, y_te = data.split_xy(splits.test, splits.features)

    # Early-stopping validation slice carved out of train
    rng = np.random.default_rng(11)
    valid_mask = rng.random(len(X_tr)) < 0.15
    X_fit, y_fit = X_tr[~valid_mask], y_tr[~valid_mask]
    X_va, y_va = X_tr[valid_mask], y_tr[valid_mask]

    models_to_train = ["ebm", "lightgbm", "logistic"]
    if CUDA_AVAILABLE:
        models_to_train.extend(["xgboost_gpu", "pytorch_gpu"])
    else:
        models_to_train.extend(["xgboost_gpu", "pytorch_gpu"])

    print(f"[{source}] Training {len(models_to_train)} models in parallel on GPU ({'CUDA' if CUDA_AVAILABLE else 'CPU'})...")
    trained_models: Dict[str, Any] = {}

    with ThreadPoolExecutor(max_workers=min(4, len(models_to_train))) as executor:
        futures = {
            executor.submit(
                _train_single_model,
                name,
                X_fit,
                y_fit,
                X_va,
                y_va,
                X_tr,
                y_tr,
                splits.categorical,
            ): name
            for name in models_to_train
        }
        for fut in as_completed(futures):
            name = futures[fut]
            try:
                m_name, model_inst = fut.result()
                trained_models[m_name] = model_inst
                print(f"  [OK] {m_name} fitted")
            except Exception as e:
                print(f"  [FAIL] {name} failed: {e}")

    # Build predictions and calibration weights for Generalized Model
    brier_scores = {}
    proba_calib = {}
    proba_test = {}

    for name, model in trained_models.items():
        p_c = model.predict_proba(X_ca)[:, 1]
        p_t = model.predict_proba(X_te)[:, 1]
        proba_calib[name] = p_c
        proba_test[name] = p_t
        brier = brier_score_loss(y_ca, p_c)
        brier_scores[name] = max(1e-4, brier)

    # Optimal weights inversely proportional to Brier loss
    inv_brier = {k: 1.0 / v for k, v in brier_scores.items()}
    sum_inv = sum(inv_brier.values())
    opt_weights = {k: v / sum_inv for k, v in inv_brier.items()}

    # Construct Generalized Model
    gen_model = GeneralizedCreditModel(trained_models, weights=opt_weights)
    trained_models["generalized_ensemble"] = gen_model
    proba_calib["generalized_ensemble"] = gen_model.predict_proba(X_ca)[:, 1]
    proba_test["generalized_ensemble"] = gen_model.predict_proba(X_te)[:, 1]

    out = {
        "source": source,
        "noise_level": noise_level,
        "n_features": len(splits.features),
        "features": splits.features,
        "models": {},
        "conformal": {},
        "ensemble_weights": opt_weights,
    }

    # Evaluate each model on Calibration and Test
    for name, model in trained_models.items():
        p_ca = proba_calib[name]
        thr = best_threshold(y_ca, p_ca)
        p_te = proba_test[name]
        out["models"][name] = {
            "calibration": evaluate(y_ca, p_ca, thr),
            "test": evaluate(y_te, p_te, thr),
        }
        if name == "ebm" and hasattr(model, "term_importances"):
            out["ebm_global_importance"] = model.term_importances()[:20]

    # Conformal calibration on Calibration Split (target 90% and 95%)
    for name in ["generalized_ensemble", "lightgbm", "ebm"]:
        if name not in trained_models:
            continue
        p_ca = np.column_stack([1.0 - proba_calib[name], proba_calib[name]])
        p_te = np.column_stack([1.0 - proba_test[name], proba_test[name]])
        entry = {}
        for alpha in (0.10, 0.05):
            for score in ("lac", "aps"):
                sc = conformal.SplitConformal(alpha=alpha, score=score).fit(p_ca, y_ca)
                entry[f"{score}_{int((1 - alpha) * 100)}"] = {
                    "threshold": round(float(sc.threshold), 4),
                    "test": conformal.evaluate_sets(sc.sets(p_te), y_te),
                }
            mond = conformal.MondrianConformal(alpha=alpha, score="lac").fit(
                p_ca, y_ca, splits.calib["_tier"]
            )
            sets = mond.sets(p_te, splits.test["_tier"])
            per_tier = {}
            for tier in sorted(set(splits.test["_tier"])):
                m = (splits.test["_tier"] == tier).to_numpy()
                if m.sum() >= 20:
                    per_tier[str(tier)] = conformal.evaluate_sets(sets[m], y_te[m])
            entry[f"mondrian_lac_{int((1 - alpha) * 100)}"] = {
                "thresholds": {k: round(v, 4) for k, v in mond.thresholds.items()},
                "test": conformal.evaluate_sets(sets, y_te),
                "per_completeness_tier": per_tier,
            }
        out["conformal"][name] = entry

    out["_models"] = trained_models
    out["_splits"] = splits
    out["_X_test"] = X_te
    return out


# --------------------------------------------------------------------------- #
# Option A Vouch Shock Evaluation
# --------------------------------------------------------------------------- #
def run_shock_evaluation(noise_level: str = "realistic") -> dict:
    """Train models on the Option A Market-Shock dataset and test vouch compensation."""
    print(f"\n[Vouch Shock Evaluation] Loading shock data with {noise_level} noise...")
    splits = data.make_shock_splits(noise_config=noise_level)
    X_tr, y_tr = data.split_xy(splits.train, splits.features)
    X_ca, y_ca = data.split_xy(splits.calib, splits.features)
    X_te, y_te = data.split_xy(splits.test, splits.features)

    # Train candidates
    models = {
        "ebm": EBMModel(interactions=0).fit(X_tr, y_tr, categorical=splits.categorical),
        "xgboost_gpu": XGBoostGPUModel(use_gpu=CUDA_AVAILABLE).fit(X_tr, y_tr),
        "pytorch_gpu": PyTorchGPUModel(epochs=30).fit(X_tr, y_tr),
        "lightgbm": LightGBMModel().fit(X_tr, y_tr, categorical=splits.categorical),
        "logistic": LogisticScorecardModel().fit(X_tr, y_tr),
    }

    # Ensemble
    brier_scores = {name: brier_score_loss(y_ca, m.predict_proba(X_ca)[:, 1]) for name, m in models.items()}
    inv_b = {k: 1.0 / max(v, 1e-4) for k, v in brier_scores.items()}
    weights = {k: v / sum(inv_b.values()) for k, v in inv_b.items()}
    gen = GeneralizedCreditModel(models, weights=weights)
    models["generalized_ensemble"] = gen

    results = {}
    for name, model in models.items():
        p_te = model.predict_proba(X_te)[:, 1]
        results[name] = evaluate(y_te, p_te, 0.5)

    # CIBIL shock vs Vouch held analysis
    se_df, vs_df, vo_df = (
        pd.read_csv(os.path.join(data.DATA_DIR, "shock_events.csv")),
        pd.read_csv(os.path.join(data.DATA_DIR, "vouch_scores.csv")).drop_duplicates(subset=["borrower_id"]),
        pd.read_csv(os.path.join(data.DATA_DIR, "vouch_outcomes.csv")).dropna(subset=["y"]).drop_duplicates(subset=["borrower_id"]),
    )
    m = se_df.merge(vs_df, on="borrower_id", how="left").merge(vo_df, on="borrower_id", how="inner")

    drop_mask = m["bureau_drop_points"] <= -30
    vh_mask = m["vouch_held"] == 1

    groups = {
        "bureau_drop_and_vouch_held": drop_mask & vh_mask,
        "bureau_drop_no_vouch": drop_mask & ~vh_mask,
        "no_bureau_drop_and_vouch_held": ~drop_mask & vh_mask,
        "no_bureau_drop_no_vouch": ~drop_mask & ~vh_mask,
    }

    crosstab = {}
    for grp_name, mask in groups.items():
        sub = m[mask]
        crosstab[grp_name] = {
            "n": int(len(sub)),
            "default_rate": round(float(sub["y"].mean()), 4) if len(sub) > 0 else None,
            "mean_bureau_drop": round(float(sub["bureau_drop_points"].mean()), 2) if len(sub) > 0 else None,
            "mean_vouch_score": round(float(sub["post_vouch_score"].mean()), 2) if len(sub) > 0 else None,
        }

    vouch_diff = None
    if "bureau_drop_and_vouch_held" in crosstab and "bureau_drop_no_vouch" in crosstab:
        g1 = m[drop_mask & vh_mask]["y"].to_numpy()
        g2 = m[drop_mask & ~vh_mask]["y"].to_numpy()
        vouch_diff = bootstrap_diff(g1, g2)

    return {
        "n_samples": len(m),
        "n_features": len(splits.features),
        "features": splits.features,
        "models": results,
        "ensemble_weights": weights,
        "shock_vouch_crosstab": crosstab,
        "vouch_risk_reduction_effect": vouch_diff,
    }


# --------------------------------------------------------------------------- #
# Vouch Association Check (Original Data)
# --------------------------------------------------------------------------- #
def vouch_analysis() -> dict:
    feats, label = data.load_raw()
    sim = feats[feats["source"] == "simulated"].join(label)
    real = feats[feats["source"] == "real_anchored"]

    vouches = pd.read_csv(os.path.join(data.DATA_DIR, "vouches.csv"))
    per = vouches.groupby("borrower_id").agg(
        n_vouch=("vouch_id", "count"),
        mean_months_known=("months_known", "mean"),
        mean_voucher_on_time=("voucher_on_time_share", "mean"),
        n_relationships=("relationship", "nunique"),
    )
    sim = sim.join(per)
    sim["n_vouch"] = sim["n_vouch"].fillna(0).astype(int)

    result = {
        "coverage": {
            "real_borrowers": int(len(real)),
            "real_borrowers_with_vouch_rows": int(real["vouch_status"].eq("OBSERVED").sum()) if "vouch_status" in real.columns else 0,
            "simulated_borrowers": int(len(sim)),
            "simulated_borrowers_with_vouch": int((sim["n_vouch"] > 0).sum()),
            "vouch_rows": int(len(vouches)),
            "max_vouches_per_borrower": int(sim["n_vouch"].max()),
        },
        "vouch_feature_matches_rows": bool((sim["vouch_count"].fillna(0) == sim["n_vouch"]).all()) if "vouch_count" in sim.columns else False,
        "default_by_vouch_count": {},
        "bureau_shock_crosstab": {},
        "incremental_auc": {},
        "verdict": {},
    }

    buckets = {
        "0": sim["n_vouch"] == 0,
        "1": sim["n_vouch"] == 1,
        "2": sim["n_vouch"] == 2,
        "3-5": sim["n_vouch"].between(3, 5),
        "6+": sim["n_vouch"] >= 6,
    }
    for lbl, msk in buckets.items():
        sub = sim[msk]
        result["default_by_vouch_count"][lbl] = {
            "n": int(len(sub)),
            "default_rate": round(float(sub["default_12m"].mean()), 4) if len(sub) else None,
        }

    shock_defs = {
        "bureau_30plus_months_gt0": sim["bureau_months_30plus_24m"].fillna(0) > 0 if "bureau_months_30plus_24m" in sim.columns else pd.Series(False, index=sim.index),
        "bureau_max_dpd_60plus": sim["bureau_max_dpd_24m"].fillna(0) >= 60 if "bureau_max_dpd_24m" in sim.columns else pd.Series(False, index=sim.index),
        "bureau_written_off_gt0": sim["bureau_written_off"].fillna(0) > 0 if "bureau_written_off" in sim.columns else pd.Series(False, index=sim.index),
    }
    for name, mask in shock_defs.items():
        bad = sim[mask]
        with_v = bad[bad["n_vouch"] > 0]["default_12m"].to_numpy()
        without_v = bad[bad["n_vouch"] == 0]["default_12m"].to_numpy()
        result["bureau_shock_crosstab"][name] = {
            "n_bad_total": int(len(bad)),
            "n_bad_with_vouch": int(len(with_v)),
            "n_bad_without_vouch": int(len(without_v)),
            "default_with_vouch": round(float(with_v.mean()), 4) if len(with_v) else None,
            "default_without_vouch": round(float(without_v.mean()), 4) if len(without_v) else None,
            "difference": bootstrap_diff(with_v, without_v),
        }

    with_v = data.make_splits(source="simulated", extra_columns=("vouch_count", "vouch_mean_voucher_on_time"))
    tr = with_v.train
    X_tr, y_tr = data.split_xy(tr, with_v.features)
    X_te, y_te = data.split_xy(with_v.test, with_v.features)
    common = [c for c in with_v.features if c not in ("vouch_count", "vouch_mean_voucher_on_time")]
    X_tr_c, X_te_c = X_tr[common], X_te[common]
    valid_mask = np.random.default_rng(11).random(len(X_tr)) < 0.15

    m_c = LightGBMModel().fit(X_tr_c[~valid_mask], y_tr[~valid_mask], X_tr_c[valid_mask], y_tr[valid_mask], with_v.categorical)
    m_v = LightGBMModel().fit(X_tr[~valid_mask], y_tr[~valid_mask], X_tr[valid_mask], y_tr[valid_mask], with_v.categorical)
    p_common = m_c.predict_proba(X_te_c)[:, 1]
    p_vouch = m_v.predict_proba(X_te)[:, 1]

    result["incremental_auc"] = {
        "auc_without_vouch": round(float(roc_auc_score(y_te, p_common)), 4),
        "auc_with_vouch": round(float(roc_auc_score(y_te, p_vouch)), 4),
        "delta": bootstrap_auc_diff(y_te, p_vouch, p_common),
    }

    result["verdict"] = {
        "recommendation": (
            "Static dataset has vouches only on simulated rows. "
            "The Option A Shock Evaluation dataset provides verified before/after score drops and outcomes."
        ),
    }
    return result


def time_holdout(source: str = "real_anchored") -> dict:
    feats, label = data.load_raw()
    feats = feats[feats["source"] == source].join(label)
    cols = data.feature_columns(feats)
    categories = {c: sorted(feats[c].dropna().unique().tolist()) for c in cols if c in data.CATEGORICAL}
    X = data.build_matrix(feats, cols, categories)

    train_m = feats["application_month"] <= "2025-03"
    test_m = feats["application_month"] >= "2025-04"
    X_tr, y_tr = X[train_m], feats.loc[train_m, "default_12m"].to_numpy()
    X_te, y_te = X[test_m], feats.loc[test_m, "default_12m"].to_numpy()

    model = EBMModel().fit(X_tr, y_tr, data.CATEGORICAL)
    p = model.predict_proba(X_te)[:, 1]
    return {"train_rows": int(train_m.sum()), "test_rows": int(test_m.sum()), "test": evaluate(y_te, p, 0.5)}


def worked_examples(model, X_test: pd.DataFrame, splits, features: list[str], raw: pd.DataFrame) -> list[dict]:
    p = model.predict_proba(X_test)[:, 1]
    order = np.argsort(p)
    picks = {
        "lowest_risk": order[0],
        "near_threshold": order[np.argmin(np.abs(p - np.median(p)))],
        "highest_risk": order[-1],
    }

    sc = conformal.SplitConformal(alpha=0.10, score="lac").fit(
        model.predict_proba(splits.calib[features]), splits.calib["_y"].to_numpy()
    )
    out = []
    for lbl, i in picks.items():
        row = X_test.iloc[[i]]
        borrower = splits.test["_id"].iloc[i] if "_id" in splits.test.columns else str(X_test.index[i])
        if hasattr(model, "eval_contributions"):
            try:
                contrib = model.eval_contributions(row)[0]
            except Exception:
                contrib = np.zeros(len(features))
        else:
            contrib = np.zeros(len(features))
        raw_row = raw.loc[borrower] if borrower in raw.index else pd.Series(dtype=object)
        member = sc.sets(model.predict_proba(row))[0]
        out.append({
            "case": lbl,
            "borrower_id": str(borrower),
            "default_probability": round(float(p[i]), 4),
            "conformal_set": {"repay": bool(member[0]), "default": bool(member[1])},
            "decision": explain.decision_from_sets(member),
            "reasons": explain.local_reasons(contrib, features, raw_row),
            "missing_information": explain.missing_information(raw_row),
        })
    return out


# --------------------------------------------------------------------------- #
# Main Multi-Version Parallel Training Engine
# --------------------------------------------------------------------------- #
def main() -> None:
    os.makedirs(MODELS_DIR, exist_ok=True)
    feats, _ = data.load_raw()

    print(f"\n{'='*70}")
    print(f"VERITRUST MULTI-MODEL CREDIT RISK ENGINE")
    print(f"CUDA Available: {CUDA_AVAILABLE} (RTX 4050 Laptop GPU)")
    print(f"{'='*70}\n")

    # 1. Standard Underwriting - Real Anchored
    print(">>> 1/4 Training Real Anchored (with Realistic Noise)...")
    real = run_source("real_anchored", noise_level="realistic")

    # 2. Standard Underwriting - Simulated
    print("\n>>> 2/4 Training Simulated (with Realistic Noise)...")
    sim = run_source("simulated", noise_level="realistic")

    # 3. Option A Vouch Shock Evaluation
    print("\n>>> 3/4 Training Option A Vouch Shock Evaluation...")
    shock_res = run_shock_evaluation(noise_level="realistic")

    # 4. Distribution shift & Holdout checks
    print("\n>>> 4/4 Evaluating Distribution Shift and Time Holdouts...")
    splits_sim = sim["_splits"] if "_splits" in sim else data.make_splits(source="simulated")
    X_sim, y_sim = data.split_xy(splits_sim.test, real["features"])
    shift = {}
    for name in ("lightgbm", "ebm", "generalized_ensemble"):
        if name in real["_models"]:
            model = real["_models"][name]
            p = model.predict_proba(X_sim)[:, 1]
            shift[name] = evaluate(y_sim, p, 0.5)

    th = time_holdout()
    va = vouch_analysis()
    ex = worked_examples(real["_models"]["ebm"], real["_X_test"], real["_splits"], real["features"], feats)

    results = {
        "hardware": {
            "cuda_available": CUDA_AVAILABLE,
            "device": "NVIDIA GeForce RTX 4050 Laptop GPU" if CUDA_AVAILABLE else "CPU",
        },
        "dataset": {
            "rows": int(len(feats)),
            "by_source": feats["source"].value_counts().to_dict(),
            "features_used": real["features"],
            "n_features": real["n_features"],
            "label_rate": {"real": 0.0819, "simulated": 0.0698},
        },
        "real_anchored": {k: v for k, v in real.items() if not k.startswith("_")},
        "simulated": {k: v for k, v in sim.items() if not k.startswith("_")},
        "vouch_shock": shock_res,
        "distribution_shift_real_to_simulated": shift,
        "time_holdout_real": th,
        "vouch_analysis": va,
        "examples": ex,
        "caveats": [
            "Data includes controlled realistic noise: 5% measurement jitter, 8% MAR missingness, 2.5% label noise.",
            "Explainable models (EBM, XGBoost GPU, PyTorch GPU, LightGBM, Logistic) run in parallel.",
            "Generalized model fuses models using inverse-Brier weights with Conformal Prediction guarantees.",
            "Vouch Shock evaluation tests Option A mechanism: does vouch held reduce defaults after a bureau drop?",
        ],
    }

    metrics_path = os.path.join(RESULTS_DIR, "metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    print(f"\nSaved metrics to {metrics_path}")

    pd.Series(real["features"]).to_csv(os.path.join(RESULTS_DIR, "features_used.csv"), index=False, header=["feature"])

    from .report import write_report
    write_report(results)
    print("All models trained, evaluated, and reported successfully!")


if __name__ == "__main__":
    main()
