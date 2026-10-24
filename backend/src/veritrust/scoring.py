"""Credibility propagation and dual-axis underwriting engine.

Implements:
1. Path traversal from institutional anchors with geometric hop decay (X = 0.5).
2. Cycle absorption with a strict PER-PATH visited-set.
3. Dual-axis underwriting: mu_composite (capacity) vs sigma2_epistemic (uncertainty).
4. Lower Confidence Bound (Score_final = mu - kappa * sqrt(sigma2)).
5. INR borrowing limit derivation.
"""

from decimal import Decimal
import math
from typing import Iterator

from veritrust.engine import TrustEngine
from veritrust.models import ContributingPath, CreditAssessment, FinancialFeatures, User


def _decimal_exp(x: Decimal, terms: int = 15) -> Decimal:
    """Compute exp(x) strictly using Decimal arithmetic (Taylor series).

    Prevents IEEE-754 float drift in exponential reputation multipliers.
    """
    result = Decimal("1.0")
    term = Decimal("1.0")
    for i in range(1, terms):
        term = term * x / Decimal(i)
        result += term
    return result


class CreditScorer:
    """Evaluates borrower creditworthiness using graph trust and financial signals."""

    def __init__(
        self,
        engine: TrustEngine,
        hop_decay: Decimal = Decimal("0.5"),
        alpha: Decimal = Decimal("0.6"),
        beta: Decimal = Decimal("0.1"),
        kappa: Decimal = Decimal("1.0"),
        base_unit_inr: Decimal = Decimal("10000.00"),
    ) -> None:
        """Initialize scorer with canonical project weights.

        Args:
            engine: The active TrustEngine instance.
            hop_decay: Geometric decay factor per intermediate hop (default 0.5).
            alpha: Weight of graph trust vs cash-flow in composite score (default 0.6).
            beta: Multiplier exponent for settled loans and incoming vouches (default 0.1).
            kappa: Epistemic uncertainty penalty parameter for LCB (default 1.0).
            base_unit_inr: Monetary scale factor per score point (default 10,000 INR).
        """
        self.engine = engine
        self.hop_decay = hop_decay
        self.alpha = alpha
        self.beta = beta
        self.kappa = kappa
        self.base_unit_inr = base_unit_inr

    def enumerate_paths(
        self,
        current: str,
        target: str,
        visited: set[str],
        current_trust: Decimal,
        hop_index: int,
        path_history: list[str],
        weight_history: list[Decimal],
    ) -> Iterator[tuple[Decimal, list[str], list[Decimal]]]:
        """Recursively enumerate all simple paths from current node to target.

        Invariant 3 (Cycle Absorption):
            The visited set is strictly PER-PATH. If a candidate neighbor is already
            in visited, the path loop yields zero trust and terminates that branch.
            A shared global visited set is strictly avoided.
        """
        if current == target:
            yield current_trust, path_history, weight_history
            return

        for neighbor in self.engine.graph.neighbors(current):
            # Invariant 3: Cycle absorption per-path
            if neighbor in visited:
                continue

            edge_weight = self.engine.graph[current][neighbor].get("weight", Decimal("0.0"))
            if edge_weight <= Decimal("0.0"):
                continue

            # Invariant 2: Hop attenuation
            # The first hop (anchor -> v1) is NOT multiplied by hop_decay; decay starts at hop_index >= 1
            attenuation = Decimal("1.0") if hop_index == 0 else self.hop_decay
            hop_trust = edge_weight * attenuation

            yield from self.enumerate_paths(
                current=neighbor,
                target=target,
                visited=visited | {neighbor},
                current_trust=current_trust * hop_trust,
                hop_index=hop_index + 1,
                path_history=path_history + [neighbor],
                weight_history=weight_history + [edge_weight],
            )

    def compute_r_graph(self, target_id: str) -> tuple[Decimal, list[ContributingPath]]:
        """Propagate and aggregate trust from all institutional anchors to target_id.

        Returns:
            Tuple of (total R_graph score, list of ContributingPath audit records).
        """
        anchors = [u.user_id for u in self.engine.list_users() if u.is_anchor and u.reputation > Decimal("0.0")]
        total_trust = Decimal("0.0")
        contributing_paths: list[ContributingPath] = []

        for anchor_id in anchors:
            if anchor_id == target_id:
                continue

            for path_trust, path_nodes, hop_weights in self.enumerate_paths(
                current=anchor_id,
                target=target_id,
                visited={anchor_id},
                current_trust=Decimal("1.0"),
                hop_index=0,
                path_history=[anchor_id],
                weight_history=[],
            ):
                if path_trust > Decimal("0.0"):
                    total_trust += path_trust
                    contributing_paths.append(
                        ContributingPath(
                            path=path_nodes,
                            hop_weights=hop_weights,
                            path_trust=path_trust,
                        )
                    )

        return total_trust, contributing_paths

    def compute_s_cashflow(self, financials: FinancialFeatures | None) -> Decimal:
        """Compute cash-flow strength score in [0.0, 1.0]."""
        if not financials:
            return Decimal("0.0")

        # 1. Debt Service Coverage Ratio (DSCR)
        # DSCR >= 1.25 considered healthy; normalize [0, 2.0] -> [0, 1.0]
        if financials.debt_service > Decimal("0.0"):
            raw_dscr = financials.net_operating_income / financials.debt_service
            dscr_norm = min(Decimal("1.0"), max(Decimal("0.0"), raw_dscr / Decimal("2.0")))
        elif financials.net_operating_income > Decimal("0.0"):
            dscr_norm = Decimal("1.0")
        else:
            dscr_norm = Decimal("0.5")

        # 2. Income Stability: lower volatility is better
        instability_norm = min(Decimal("1.0"), max(Decimal("0.0"), financials.income_volatility))
        stability_score = Decimal("1.0") - instability_norm

        # 3. Cash-flow Volatility
        volatility_norm = min(Decimal("1.0"), max(Decimal("0.0"), financials.cashflow_volatility))
        volatility_score = Decimal("1.0") - volatility_norm

        # Weighted combination scaled by completeness
        w1, w2, w3 = Decimal("0.5"), Decimal("0.3"), Decimal("0.2")
        raw_score = (w1 * dscr_norm) + (w2 * stability_score) + (w3 * volatility_score)
        completeness = min(Decimal("1.0"), max(Decimal("0.0"), financials.completeness))

        return raw_score * completeness

    def compute_epistemic_uncertainty(
        self, user: User, completeness: Decimal, in_degree: int
    ) -> Decimal:
        """Calculate epistemic uncertainty sigma2 in [0.0, 1.0].

        Formula:
            sigma2 = 1 / (1 + N_data_points * completeness)
        A cold-start user (0 settled loans, 0 vouches, 0 data) has sigma2 = 1.0.
        """
        n_data_points = Decimal(user.n_settled_loans + in_degree)
        if user.financial_features is not None:
            n_data_points += Decimal("1.0")

        denominator = Decimal("1.0") + (n_data_points * completeness)
        if denominator <= Decimal("0.0"):
            return Decimal("1.0")

        sigma2 = Decimal("1.0") / denominator
        # Bound strictly between [0.0, 1.0]
        return min(Decimal("1.0"), max(Decimal("0.0"), sigma2))

    def assess_credit(self, user_id: str) -> CreditAssessment:
        """Produce a complete, explainable dual-axis credit assessment for user_id."""
        user = self.engine.get_user(user_id)
        if not user:
            raise ValueError(f"User '{user_id}' does not exist.")

        # Defaulted nodes receive zero limit immediately
        if user.status == "DEFAULTED":
            return CreditAssessment(
                user_id=user_id,
                r_graph=Decimal("0.0"),
                s_cashflow=Decimal("0.0"),
                mu_composite=Decimal("0.0"),
                sigma2_epistemic=Decimal("1.0"),
                score_final=Decimal("0.0"),
                max_loan_limit=Decimal("0.0"),
                contributing_paths=[],
            )

        # 1. Graph propagation
        r_graph, contributing_paths = self.compute_r_graph(user_id)

        # 2. Cash-flow score
        s_cashflow = self.compute_s_cashflow(user.financial_features)

        # 3. Incoming vouches count |In(T)|
        in_edges = list(self.engine.graph.in_edges(user_id))
        in_degree = len(in_edges)

        # 4. Composite expected capacity: mu_composite
        # (alpha * R_graph + (1 - alpha) * S_cashflow) * exp(beta * (N_settled + |In(T)|))
        base_capacity = (self.alpha * r_graph) + ((Decimal("1.0") - self.alpha) * s_cashflow)
        multiplier_exponent = self.beta * Decimal(user.n_settled_loans + in_degree)
        capacity_multiplier = _decimal_exp(multiplier_exponent)
        mu_composite = base_capacity * capacity_multiplier

        # 5. Epistemic uncertainty: sigma2_epistemic
        completeness = (
            user.financial_features.completeness
            if user.financial_features
            else Decimal("0.0")
        )
        sigma2 = self.compute_epistemic_uncertainty(user, completeness, in_degree)

        # 6. Lower Confidence Bound (Score_final = mu - kappa * sqrt(sigma2))
        sigma = sigma2.sqrt()
        score_final = mu_composite - (self.kappa * sigma)

        # 7. Maximum loan limit
        if score_final > Decimal("0.0"):
            max_loan = (score_final * self.base_unit_inr).quantize(Decimal("1.00"))
        else:
            max_loan = Decimal("0.00")

        return CreditAssessment(
            user_id=user_id,
            r_graph=r_graph.quantize(Decimal("0.0001")),
            s_cashflow=s_cashflow.quantize(Decimal("0.0001")),
            mu_composite=mu_composite.quantize(Decimal("0.0001")),
            sigma2_epistemic=sigma2.quantize(Decimal("0.0001")),
            score_final=score_final.quantize(Decimal("0.0001")),
            max_loan_limit=max_loan,
            contributing_paths=contributing_paths,
        )

