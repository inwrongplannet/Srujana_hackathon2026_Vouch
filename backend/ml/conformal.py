"""Split-conformal prediction for the default classifier.

Why this exists: a probability is not a decision. Conformal sets give a
distribution-free guarantee ("the true label is in the set with probability
>= 1 - alpha") and the set size is the honest uncertainty signal the demo needs.

Two scores are implemented:
  LAC  - 1 - p(y|x). Small sets, weak on rare classes.
  APS  - cumulative mass up to and including y, randomised by u ~ U(0,1).
Both are applied once globally and once per completeness tier (Mondrian), so a
thin-file applicant is not held to the coverage promised for a rich-file one.
"""

from __future__ import annotations

import numpy as np


def _quantile(scores: np.ndarray, alpha: float) -> float:
    """Finite-sample conformal quantile: ceil((n+1)(1-alpha))/n."""
    n = len(scores)
    if n == 0:
        return 1.0
    k = int(np.ceil((n + 1) * (1 - alpha)))
    k = min(max(k, 1), n)
    return float(np.sort(scores)[k - 1])


def lac_scores(proba: np.ndarray, y: np.ndarray | None = None) -> np.ndarray:
    """Nonconformity = 1 - probability of the true (or each) label."""
    if y is None:
        return 1.0 - proba
    return 1.0 - proba[np.arange(len(y)), y]


def aps_scores(proba: np.ndarray, y: np.ndarray, u: float = 0.5) -> np.ndarray:
    """Adaptive prediction set score; u fixes the randomisation for determinism."""
    order = np.argsort(-proba, axis=1)
    sorted_p = np.take_along_axis(proba, order, axis=1)
    cum = np.cumsum(sorted_p, axis=1)
    rank = np.argmax(order == y[:, None], axis=1)
    return cum[np.arange(len(y)), rank] - u * sorted_p[np.arange(len(y)), rank]


def prediction_sets(proba: np.ndarray, threshold: float, score: str = "lac") -> np.ndarray:
    """Boolean set membership (n_samples, 2) for the given conformal threshold."""
    if score == "lac":
        return (1.0 - proba) <= threshold + 1e-12
    order = np.argsort(-proba, axis=1)
    sorted_p = np.take_along_axis(proba, order, axis=1)
    cum_prev = np.cumsum(sorted_p, axis=1) - sorted_p  # mass strictly before each class
    member = np.zeros_like(proba, dtype=bool)
    for i in range(len(proba)):
        keep = cum_prev[i] < threshold
        member[i, order[i][keep]] = True
    return member


def evaluate_sets(sets: np.ndarray, y: np.ndarray) -> dict:
    """Empirical coverage, average set size and set composition."""
    sizes = sets.sum(axis=1)
    covered = sets[np.arange(len(y)), y]
    return {
        "n": int(len(y)),
        "coverage": float(covered.mean()),
        "avg_set_size": float(sizes.mean()),
        "singleton_rate": float((sizes == 1).mean()),
        "empty_rate": float((sizes == 0).mean()),
        "full_rate": float((sizes == 2).mean()),
        "both_label_rate": float(((sets[:, 0]) & (sets[:, 1])).mean()),
    }


class SplitConformal:
    """Global (marginal) split conformal for a binary classifier."""

    def __init__(self, alpha: float = 0.10, score: str = "lac"):
        self.alpha = alpha
        self.score = score
        self.threshold: float | None = None

    def fit(self, calib_proba: np.ndarray, calib_y: np.ndarray) -> "SplitConformal":
        s = lac_scores(calib_proba, calib_y) if self.score == "lac" else aps_scores(calib_proba, calib_y)
        self.threshold = _quantile(s, self.alpha)
        return self

    def sets(self, proba: np.ndarray) -> np.ndarray:
        if self.threshold is None:
            raise RuntimeError("call fit() first")
        return prediction_sets(proba, self.threshold, self.score)


class MondrianConformal:
    """One conformal threshold per completeness tier (conditional coverage)."""

    def __init__(self, alpha: float = 0.10, score: str = "lac"):
        self.alpha = alpha
        self.score = score
        self.thresholds: dict[str, float] = {}

    def fit(self, calib_proba: np.ndarray, calib_y: np.ndarray, tiers) -> "MondrianConformal":
        tiers = np.asarray(tiers)
        for tier in sorted(set(tiers)):
            m = tiers == tier
            s = lac_scores(calib_proba[m], calib_y[m])
            self.thresholds[str(tier)] = _quantile(s, self.alpha)
        return self

    def sets(self, proba: np.ndarray, tiers) -> np.ndarray:
        tiers = np.asarray(tiers)
        out = np.zeros((len(proba), 2), dtype=bool)
        for tier in sorted(set(tiers)):
            m = tiers == tier
            thr = self.thresholds.get(str(tier), 1.0)
            out[m] = prediction_sets(proba[m], thr, self.score)
        return out
