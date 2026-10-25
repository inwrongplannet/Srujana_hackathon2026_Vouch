"""Ablation study evaluating the incremental predictive and inclusion value of VeriTrust.

Informed by the literature review:
1. Invisible Primes (Di Maggio & Ratnadiwakara, 2026): Does alternative data identify creditworthy thin-file borrowers?
2. Network Centrality (Finance Research Letters, 2024): Does VeriTrust outperform simple degree centrality?
3. DeepCredit (AAAI ICWSM, 2018): Does behavioral/support timing matter beyond static counts?
4. Social Media Fusing (Procedia CS, 2016): Does endorser quality beat raw connection counts?
5. Interpretability & Fairness (Decision Support Systems 2022, Giudici 2024): Provenance traces and subgroup inclusion.

Ablation hierarchy:
- Model A: Conventional Financial & Bureau Features Only (Baseline)
- Model B: Model A + Simple Network Topology (Degree Centrality, Clusters, Reciprocity)
- Model C: Model B + Endorser Quality & Direct Stake (Reliability, Weights, Pre-Application Support)
- Model D: Model C + Full VeriTrust Framework (Propagated Credibility, Rank Attenuation, Vouch Held)
- Model E: Specific Component Removals (No Rank Discount, No Pre-App Support, Graph-Only Cold Start)
- Subgroup Analysis: Thin-File / Unscorable vs Established Bureau Borrowers.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    f1_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split

from .conformal import SplitConformal, evaluate_sets
from .models import (
    EBMModel,
    GeneralizedCreditModel,
    LightGBMModel,
    LogisticScorecardModel,
    PyTorchGPUModel,
    XGBoostGPUModel,
    CUDA_AVAILABLE,
)
from .noise import NOISE_PRESETS, inject_realistic_noise
from .train import bootstrap_auc_diff, bootstrap_diff

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "combined")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


# --------------------------------------------------------------------------- #
# Feature Sets Defining the Ablation Levels
# --------------------------------------------------------------------------- #
FEATURES_MODEL_A = [
    # Conventional financial & bureau metrics
    "pre_bureau_score",
    "post_bureau_score",
    "bureau_drop_points",
    "bureau_shock",
    "shock_type",
    "severity",
    "insured",
    "expense_minor",
    "income_factor",
    "income_est_minor",
    "dti_est",
    "bank_surplus_median_minor",
    "bank_income_cv",
    "new_emi_minor",
]

FEATURES_MODEL_B = FEATURES_MODEL_A + [
    # Simple network topology (degree centrality baseline)
    "eligible_incoming",       # in-degree centrality
    "distinct_anchors",        # raw connection count
    "reciprocal_edges",        # bidirectional edge count
    "cluster_concentration",   # local network density
]

FEATURES_MODEL_C = FEATURES_MODEL_B + [
    # Endorser quality & direct financial commitment
    "total_weight",
    "mean_voucher_reliability",
    "max_contributor_share",
    "support_before_application_minor",
]

FEATURES_MODEL_D = FEATURES_MODEL_C + [
    # Full VeriTrust mathematical propagation framework
    "pre_vouch_score",
    "post_vouch_score",
    "vouch_held",
]

# Component-level variations
FEATURES_NO_RANK_OR_PROPAGATION = [f for f in FEATURES_MODEL_D if f not in ("pre_vouch_score", "post_vouch_score")]
FEATURES_NO_PRE_SUPPORT = [f for f in FEATURES_MODEL_D if f != "support_before_application_minor"]
FEATURES_GRAPH_ONLY_COLD_START = [
    f for f in FEATURES_MODEL_D
    if f not in ("pre_bureau_score", "post_bureau_score", "bureau_drop_points", "bureau_shock")
]


# --------------------------------------------------------------------------- #
# Data Loading & Merging
# --------------------------------------------------------------------------- #
def load_ablation_dataset() -> Tuple[pd.DataFrame, np.ndarray]:
    """Load joined dataset combining shock events, vouch metrics, outcomes, and financial features."""
    se = pd.read_csv(os.path.join(DATA_DIR, "shock_events.csv"), low_memory=False)
    vs = pd.read_csv(os.path.join(DATA_DIR, "vouch_scores.csv"), low_memory=False).drop_duplicates(subset=["borrower_id"])
    vo = pd.read_csv(os.path.join(DATA_DIR, "vouch_outcomes.csv"), low_memory=False).dropna(subset=["y"]).drop_duplicates(subset=["borrower_id"])
    feats = pd.read_csv(os.path.join(DATA_DIR, "features.csv"), low_memory=False).set_index("borrower_id")

    # Merge on borrower_id
    m = se.merge(vs, on="borrower_id", how="left").merge(vo, on="borrower_id", how="inner")
    m = m.join(feats, on="borrower_id", suffixes=("", "_feat"))

    # Encode categoricals
    for c in ["shock_type", "severity"]:
        if c in m.columns:
            cats = sorted(m[c].dropna().unique().tolist())
            mapping = {v: i for i, v in enumerate(cats)}
            m[c] = m[c].map(mapping).fillna(-1).astype(float)

    y = m["y"].to_numpy().astype(int)
    return m, y


# --------------------------------------------------------------------------- #
# Evaluation Helper
# --------------------------------------------------------------------------- #
def evaluate_predictions(y_true: np.ndarray, proba: np.ndarray, threshold: float = 0.5) -> Dict[str, Any]:
    p1 = proba[:, 1] if proba.ndim == 2 else proba
    pred = (p1 >= threshold).astype(int)
    fpr, tpr, _ = roc_curve(y_true, p1)
    ks = float(np.max(tpr - fpr))

    return {
        "n": int(len(y_true)),
        "auc": round(float(roc_auc_score(y_true, p1)), 4),
        "pr_auc": round(float(average_precision_score(y_true, p1)), 4),
        "brier": round(float(brier_score_loss(y_true, p1)), 4),
        "ks": round(ks, 4),
        "accuracy": round(float(accuracy_score(y_true, pred)), 4),
        "f1": round(float(f1_score(y_true, pred, zero_division=0)), 4),
        "approval_rate": round(float((pred == 0).mean()), 4),
    }


# --------------------------------------------------------------------------- #
# Main Ablation Runner
# --------------------------------------------------------------------------- #
def run_ablation_study(seed: int = 42, noise_level: str = "realistic") -> Dict[str, Any]:
    print(f"\n{'='*75}")
    print(f"VERITRUST ABLATION STUDY: PROVING VALUE OVER BASELINES")
    print(f"CUDA Available: {CUDA_AVAILABLE} (RTX 4050 Laptop GPU)")
    print(f"Noise Profile: {noise_level}")
    print(f"{'='*75}\n")

    m, y = load_ablation_dataset()
    n_total = len(m)
    print(f"Loaded {n_total} records with resolved outcomes (Default rate: {y.mean():.2%})\n")

    # Define all ablation configurations
    ablation_levels = {
        "Level_A_Conventional_Baseline": {
            "name": "Model A: Conventional Financial & Bureau Only",
            "features": [f for f in FEATURES_MODEL_A if f in m.columns],
            "description": "Standard bureau & fintech features without social/network data",
        },
        "Level_B_Degree_Centrality": {
            "name": "Model B: A + Simple Network Topology (Degree Centrality)",
            "features": [f for f in FEATURES_MODEL_B if f in m.columns],
            "description": "Adds degree centrality, cluster density, and edge count",
        },
        "Level_C_Endorser_Quality": {
            "name": "Model C: B + Endorser Reliability & Direct Stake",
            "features": [f for f in FEATURES_MODEL_C if f in m.columns],
            "description": "Adds voucher historical reliability and pre-application support",
        },
        "Level_D_Full_VeriTrust": {
            "name": "Model D: Full VeriTrust Reputation Framework",
            "features": [f for f in FEATURES_MODEL_D if f in m.columns],
            "description": "Adds multi-hop propagation, chronological rank discount, and vouch held",
        },
        "Level_E1_No_Rank_Discount": {
            "name": "Model E1: VeriTrust without Rank Discount / Attenuation",
            "features": [f for f in FEATURES_NO_RANK_OR_PROPAGATION if f in m.columns],
            "description": "Tests vulnerability to raw connection counts without rank discount",
        },
        "Level_E2_No_Pre_Support": {
            "name": "Model E2: VeriTrust without Pre-Application Liquidity Support",
            "features": [f for f in FEATURES_NO_PRE_SUPPORT if f in m.columns],
            "description": "Evaluates pure graph reputation without direct financial support",
        },
        "Level_E3_Graph_Only_Cold_Start": {
            "name": "Model E3: VeriTrust Graph-Only (Unscorable / Thin-File Cold Start)",
            "features": [f for f in FEATURES_GRAPH_ONLY_COLD_START if f in m.columns],
            "description": "Zero traditional bureau history; relying purely on social collateral",
        },
    }

    # Stratified 60/20/20 train/calib/test split
    idx = np.arange(len(m))
    idx_tr, idx_test = train_test_split(idx, test_size=0.20, random_state=seed, stratify=y)
    idx_tr, idx_calib = train_test_split(idx_tr, test_size=0.25, random_state=seed, stratify=y[idx_tr])

    results: Dict[str, Any] = {
        "n_samples": n_total,
        "n_train": len(idx_tr),
        "n_calib": len(idx_calib),
        "n_test": len(idx_test),
        "noise_profile": noise_level,
        "levels": {},
    }

    # Store test probability predictions for bootstrap comparisons
    predictions_test: Dict[str, np.ndarray] = {}

    for lvl_key, cfg in ablation_levels.items():
        feats = cfg["features"]
        X_all = m[feats].copy()

        # Add informative missingness indicators
        for col in feats[:]:
            if X_all[col].isna().any():
                flag = f"{col}_was_missing"
                X_all[flag] = X_all[col].isna().astype(float)
                if flag not in feats:
                    feats.append(flag)

        # Apply realistic noise to training split
        if noise_level != "clean":
            noise_cfg = NOISE_PRESETS[noise_level]
            X_tr_noisy, y_tr_noisy, _ = inject_realistic_noise(
                X_all.iloc[idx_tr], y[idx_tr], noise_cfg, seed=seed
            )
        else:
            X_tr_noisy = X_all.iloc[idx_tr].copy()
            y_tr_noisy = y[idx_tr].copy()

        X_ca = X_all.iloc[idx_calib].copy()
        y_ca = y[idx_calib].copy()
        X_te = X_all.iloc[idx_test].copy()
        y_te = y[idx_test].copy()

        print(f"Training [{cfg['name']}] ({len(feats)} features)...")

        # Train model suite
        models = {
            "xgboost_gpu": XGBoostGPUModel(n_estimators=500, use_gpu=CUDA_AVAILABLE).fit(X_tr_noisy, y_tr_noisy),
            "pytorch_gpu": PyTorchGPUModel(hidden_dim=64, epochs=30).fit(X_tr_noisy, y_tr_noisy),
            "lightgbm": LightGBMModel(n_estimators=500).fit(X_tr_noisy, y_tr_noisy),
            "logistic": LogisticScorecardModel().fit(X_tr_noisy, y_tr_noisy),
        }

        # Calibration weights for Generalized Ensemble
        brier_scores = {k: brier_score_loss(y_ca, mod.predict_proba(X_ca)[:, 1]) for k, mod in models.items()}
        inv_brier = {k: 1.0 / max(v, 1e-4) for k, v in brier_scores.items()}
        weights = {k: v / sum(inv_brier.values()) for k, v in inv_brier.items()}
        ensemble = GeneralizedCreditModel(models, weights=weights)
        models["generalized_ensemble"] = ensemble

        # Conformal sets for Generalized Ensemble
        p_ca_ens = ensemble.predict_proba(X_ca)
        p_te_ens = ensemble.predict_proba(X_te)
        sc = SplitConformal(alpha=0.10, score="lac").fit(p_ca_ens, y_ca)
        sets_te = sc.sets(p_te_ens)
        conf_eval = evaluate_sets(sets_te, y_te)

        # Evaluate all models on held-out test split
        level_metrics = {}
        for mod_name, mod in models.items():
            p_te = mod.predict_proba(X_te)
            level_metrics[mod_name] = evaluate_predictions(y_te, p_te)

        predictions_test[lvl_key] = p_te_ens[:, 1]

        results["levels"][lvl_key] = {
            "name": cfg["name"],
            "description": cfg["description"],
            "n_features": len(feats),
            "features": feats,
            "models": level_metrics,
            "conformal_90": {
                "threshold": round(float(sc.threshold), 4),
                "coverage": round(float(conf_eval["coverage"]), 4),
                "avg_set_size": round(float(conf_eval["avg_set_size"]), 3),
                "singleton_rate": round(float(conf_eval["singleton_rate"]), 3),
            },
        }

    # ----------------------------------------------------------------------- #
    # Statistical Bootstrap Hypothesis Testing
    # ----------------------------------------------------------------------- #
    y_test_arr = y[idx_test]
    p_baseline = predictions_test["Level_A_Conventional_Baseline"]
    p_degree = predictions_test["Level_B_Degree_Centrality"]
    p_veritrust = predictions_test["Level_D_Full_VeriTrust"]

    print("\nCalculating bootstrap statistical deltas...")
    delta_veritrust_vs_conventional = bootstrap_auc_diff(y_test_arr, p_veritrust, p_baseline)
    delta_veritrust_vs_degree = bootstrap_auc_diff(y_test_arr, p_veritrust, p_degree)
    delta_degree_vs_conventional = bootstrap_auc_diff(y_test_arr, p_degree, p_baseline)

    results["hypothesis_tests"] = {
        "veritrust_vs_conventional_baseline": {
            "delta_auc": delta_veritrust_vs_conventional["delta_auc"],
            "ci_95": [delta_veritrust_vs_conventional["ci_low"], delta_veritrust_vs_conventional["ci_high"]],
            "statistically_significant": delta_veritrust_vs_conventional["significant"],
        },
        "veritrust_vs_degree_centrality": {
            "delta_auc": delta_veritrust_vs_degree["delta_auc"],
            "ci_95": [delta_veritrust_vs_degree["ci_low"], delta_veritrust_vs_degree["ci_high"]],
            "statistically_significant": delta_veritrust_vs_degree["significant"],
        },
        "degree_centrality_vs_conventional": {
            "delta_auc": delta_degree_vs_conventional["delta_auc"],
            "ci_95": [delta_degree_vs_conventional["ci_low"], delta_degree_vs_conventional["ci_high"]],
            "statistically_significant": delta_degree_vs_conventional["significant"],
        },
    }

    # ----------------------------------------------------------------------- #
    # Subgroup Fairness & Financial Inclusion (Invisible Primes Analysis)
    # ----------------------------------------------------------------------- #
    print("\nRunning Subgroup Inclusion Analysis (Thin-File vs Established)...")
    m_test = m.iloc[idx_test].copy()
    m_test["p_conventional"] = p_baseline
    m_test["p_veritrust"] = p_veritrust
    m_test["pred_conventional"] = (p_baseline >= 0.5).astype(int)
    m_test["pred_veritrust"] = (p_veritrust >= 0.5).astype(int)
    m_test["true_y"] = y_test_arr

    # Define Thin-File / Unscorable borrowers (bureau drop <= -40 or low traditional baseline)
    shock_subgroup = m_test["bureau_drop_points"] <= -30
    subgroup_analysis = {}

    for name, mask in [("All_Test_Borrowers", pd.Series(True, index=m_test.index)),
                       ("Severe_Bureau_Shock_Borrowers", shock_subgroup),
                       ("Stable_Bureau_Borrowers", ~shock_subgroup)]:
        sub = m_test[mask]
        if len(sub) == 0:
            continue
        subgroup_analysis[name] = {
            "n": int(len(sub)),
            "default_rate": round(float(sub["true_y"].mean()), 4),
            "conventional_approval_rate": round(float((sub["pred_conventional"] == 0).mean()), 4),
            "veritrust_approval_rate": round(float((sub["pred_veritrust"] == 0).mean()), 4),
            "approval_rate_gain": round(float((sub["pred_veritrust"] == 0).mean() - (sub["pred_conventional"] == 0).mean()), 4),
            "conventional_auc": round(float(roc_auc_score(sub["true_y"], sub["p_conventional"])), 4),
            "veritrust_auc": round(float(roc_auc_score(sub["true_y"], sub["p_veritrust"])), 4),
        }

    # Identify Invisible Primes: rejected by Conventional model but approved by VeriTrust
    invisible_primes = m_test[(m_test["pred_conventional"] == 1) & (m_test["pred_veritrust"] == 0)]
    results["subgroups"] = subgroup_analysis
    results["invisible_primes"] = {
        "n_unlocked": int(len(invisible_primes)),
        "share_of_rejected_unlocked": round(float(len(invisible_primes) / max(1, (m_test['pred_conventional'] == 1).sum())), 4),
        "default_rate_of_unlocked": round(float(invisible_primes["true_y"].mean()), 4) if len(invisible_primes) else None,
        "population_default_rate": round(float(m_test["true_y"].mean()), 4),
    }

    # Save metrics JSON
    os.makedirs(RESULTS_DIR, exist_ok=True)
    out_file = os.path.join(RESULTS_DIR, "ablation_study.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[Ablation Complete] Results written to {out_file}\n")
    return results


if __name__ == "__main__":
    run_ablation_study(seed=42, noise_level="realistic")

