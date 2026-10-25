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
from typing import Iterator, Optional

from veritrust.config import get_settings
from veritrust.engine import TrustEngine
from veritrust.models import (
    BureauReport,
    BureauStatus,
    CombinedAssessment,
    ContributingPath,
    CreditAssessment,
    FinancialFeatures,
    LoanApplication,
    PropagatedCredibilityReport,
    User,
    VouchScoreReport,
)


def _decimal_exp(x: Decimal, terms: int = 40) -> Decimal:
    """Compute exp(x) strictly using Decimal arithmetic (Taylor series).

    For x < 0, computes 1 / exp(-x) to prevent catastrophic alternating series
    cancellation. Prevents IEEE-754 float drift in exponential multipliers.
    """
    if x == Decimal("0.0"):
        return Decimal("1.0")

    if x < Decimal("0.0"):
        pos_x = -x
        if pos_x > Decimal("50.0"):
            return Decimal("0.0")
        exp_pos = _decimal_exp(pos_x, terms=terms)
        if exp_pos == Decimal("0.0"):
            return Decimal("0.0")
        return Decimal("1.0") / exp_pos

    # For x > 0, compute Taylor series with dynamic convergence tolerance
    result = Decimal("1.0")
    term = Decimal("1.0")
    for i in range(1, terms):
        term = term * x / Decimal(i)
        result += term
        if term < Decimal("1e-12"):
            break
    return result


class CreditScorer:
    """Evaluates borrower creditworthiness using graph trust and financial signals."""

    def __init__(
        self,
        engine: TrustEngine,
        hop_decay: Optional[Decimal] = None,
        alpha: Optional[Decimal] = None,
        beta: Optional[Decimal] = None,
        kappa: Optional[Decimal] = None,
        base_unit_inr: Optional[Decimal] = None,
    ) -> None:
        """Initialize scorer with configurable parameters.

        Args:
            engine: The active TrustEngine instance.
            hop_decay: Geometric decay factor per intermediate hop (fallback: config/env).
            alpha: Weight of graph trust vs cash-flow in composite score (fallback: config/env).
            beta: Multiplier exponent for settled loans and incoming vouches (fallback: config/env).
            kappa: Epistemic uncertainty penalty parameter k / kappa for LCB (fallback: config/env).
            base_unit_inr: Monetary scale factor per score point (fallback: config/env).
        """
        settings = get_settings()
        self.engine = engine
        self.hop_decay = hop_decay if hop_decay is not None else settings.hop_decay
        self.alpha = alpha if alpha is not None else settings.alpha
        self.beta = beta if beta is not None else settings.beta
        self.kappa = kappa if kappa is not None else settings.kappa
        self.base_unit_inr = base_unit_inr if base_unit_inr is not None else settings.base_unit_inr

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

    def compute_propagated_credibility(
        self,
        target_id: str,
        delta: Optional[Decimal] = None,
        g_max: Optional[Decimal] = None,
        sources_only: Optional[list[str]] = None,
    ) -> PropagatedCredibilityReport:
        """Consolidate propagated credibility across the endorsement graph.

        Implements Sections 6, 7, 8, 9 of Master Mathematical Framework (2026):
            T(P) = R_s * (prod 1/d_v_i) * (prod alpha_v_i_v_i+1) * delta^(h-1)
            p_u(s) = min_{P in P(s, u)} T(P)   (Min-path consolidation per source)
            G(u) = sum_{s != u} p_u(s)          (Distinct original source aggregation)
            G_score(u) = min(G(u), G_max)       (Scoring cap)
        """
        import networkx as nx
        settings = get_settings()
        decay_delta = delta if delta is not None else settings.hop_decay_delta
        cap_max = g_max if g_max is not None else settings.g_max

        all_paths_evaluated: list[ContributingPath] = []
        source_paths_map: dict[str, list[Decimal]] = {}

        # Candidate sources: all nodes s != target_id with owned reputation R_s > 0
        if sources_only is not None:
            candidate_sources = [s for s in sources_only if s != target_id]
        else:
            candidate_sources = [
                u.user_id
                for u in self.engine.list_users()
                if u.user_id != target_id and u.reputation > Decimal("0.0")
            ]

        for s in candidate_sources:
            if not self.engine.graph.has_node(s) or not self.engine.graph.has_node(target_id):
                continue

            source_user = self.engine.get_user(s)
            r_s = source_user.reputation if source_user else Decimal("0.0")
            if r_s <= Decimal("0.0"):
                continue

            # Enumerate simple paths from s to target_id (per-path cycle elimination)
            try:
                paths_gen = nx.all_simple_paths(self.engine.graph, source=s, target=target_id)
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue

            for path in paths_gen:
                h = len(path) - 1
                if h < 1:
                    continue

                # Term 1: R_s
                # Term 2: prod_{i=0}^{h-1} (1 / d_{v_i})
                # Term 3: prod_{i=0}^{h-1} alpha_{v_i v_{i+1}}
                out_deg_product = Decimal("1.0")
                rank_alpha_product = Decimal("1.0")
                hop_weights: list[Decimal] = []

                valid_path = True
                for i in range(h):
                    curr_node = path[i]
                    next_node = path[i + 1]

                    out_degree = len(list(self.engine.graph.out_edges(curr_node)))
                    if out_degree == 0:
                        valid_path = False
                        break

                    out_deg_product *= (Decimal("1.0") / Decimal(out_degree))

                    edge_data = self.engine.graph[curr_node][next_node]
                    edge_alpha = edge_data.get("alpha", Decimal("1.0"))
                    edge_weight = edge_data.get("weight", Decimal("0.0"))
                    rank_alpha_product *= edge_alpha
                    hop_weights.append(edge_weight)

                if not valid_path:
                    continue

                # Term 4: delta^(h - 1)
                hop_attenuation = Decimal("1.0")
                if h > 1 and decay_delta > Decimal("0.0"):
                    hop_attenuation = decay_delta ** (h - 1)

                t_p = (r_s * out_deg_product * rank_alpha_product * hop_attenuation).quantize(Decimal("0.0001"))

                if s not in source_paths_map:
                    source_paths_map[s] = []
                source_paths_map[s].append(t_p)

                all_paths_evaluated.append(
                    ContributingPath(
                        path=path,
                        hop_weights=hop_weights,
                        path_trust=t_p,
                    )
                )

        # Section 8: Same-source consolidation -> min_{P in P(s, u)} T(P)
        p_u_s: dict[str, Decimal] = {}
        for s, path_trusts in source_paths_map.items():
            if path_trusts:
                p_u_s[s] = min(path_trusts)

        # Section 9: Aggregate distinct sources -> G(u) = sum_{s != u} p_u(s)
        g_raw = sum(p_u_s.values(), Decimal("0.0")).quantize(Decimal("0.0001"))

        # Scoring cap: G_score(u) = min(G(u), G_max)
        g_score = min(g_raw, cap_max).quantize(Decimal("0.0001"))

        return PropagatedCredibilityReport(
            user_id=target_id,
            g_raw=g_raw,
            g_score=g_score,
            source_contributions=p_u_s,
            paths=all_paths_evaluated,
        )

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

    @staticmethod
    def compute_endorsement_weight(
        r_x: Decimal,
        q_x: Decimal = Decimal("1.0"),
        e_xy: Decimal = Decimal("1.0"),
        d_xy: Decimal = Decimal("1.0"),
        p_xy: Decimal = Decimal("0.0"),
    ) -> Decimal:
        """Calculate effective edge weight (Section 6.1 of Master Doc v2).

        w_xy = clamp(r_x * q_x * e_xy * d_xy * (1 - p_xy), 0, 1)
        """
        raw = r_x * q_x * e_xy * d_xy * (Decimal("1.0") - p_xy)
        return min(Decimal("1.0"), max(Decimal("0.0"), raw))

    def compute_vouch_score(
        self, target_id: str, tau: Decimal = Decimal("3.0")
    ) -> VouchScoreReport:
        """Calculate bounded Vouch Score in [0, 100] (Section 6.2 of Master Doc v2).

        tau = 3, the Vouch scoring proposal's value, shared with the frontend (docs/DECISIONS.md).
        W = sum(w_xy) for all incoming eligible endorsements.
        support = 1 - exp(-W / tau)
        quality = clamp(C, 0, 1)
        VouchScore = round(100 * support * (0.35 + 0.65 * quality))
        """
        user = self.engine.get_user(target_id)
        if not user:
            return VouchScoreReport()

        in_edges = list(self.engine.graph.in_edges(target_id))
        total_w = Decimal("0.0")
        total_settled = 0
        total_defaults = 0

        for source_id, _ in in_edges:
            edge_data = self.engine.graph[source_id][target_id]
            edge_weight = edge_data.get("weight", Decimal("0.0"))
            edge_alpha = edge_data.get("alpha", Decimal("1.0"))
            source_user = self.engine.get_user(source_id)
            if not source_user:
                continue

            r_x = min(Decimal("1.0"), max(Decimal("0.0"), source_user.reputation / Decimal("10.0")))
            q_x = Decimal("1.0") if source_user.is_anchor else Decimal("0.85")
            e_xy = Decimal("1.0") if source_user.status == "ACTIVE" else Decimal("0.0")
            d_xy = Decimal("1.0")
            p_xy = Decimal("0.0")

            w_xy = self.compute_endorsement_weight(r_x, q_x, e_xy, d_xy, p_xy)
            total_w += edge_weight * edge_alpha * w_xy

            total_settled += source_user.n_settled_loans
            if source_user.status == "DEFAULTED":
                total_defaults += 1

        # Laplace smoothing quality factor C
        c_denom = Decimal(total_settled + total_defaults + 2)
        c_factor = Decimal(total_settled + 1) / c_denom
        quality = min(Decimal("1.0"), max(Decimal("0.0"), c_factor))

        # Support with diminishing returns: 1 - exp(-W / tau)
        if total_w > Decimal("0.0") and tau > Decimal("0.0"):
            neg_exponent = -(total_w / tau)
            support = Decimal("1.0") - _decimal_exp(neg_exponent)
            support = min(Decimal("1.0"), max(Decimal("0.0"), support))
        else:
            support = Decimal("0.0")

        raw_vouch_score = Decimal("100.0") * support * (Decimal("0.35") + (Decimal("0.65") * quality))
        vouch_score = raw_vouch_score.quantize(Decimal("1.0"))

        confidence = "LOW"
        if len(in_edges) >= 3 and total_w >= Decimal("2.0"):
            confidence = "HIGH"
        elif len(in_edges) >= 1:
            confidence = "MEDIUM"

        status = "PROVISIONAL" if user.n_settled_loans == 0 and not in_edges else "ACTIVE"

        return VouchScoreReport(
            vouch_score=vouch_score,
            status=status,
            confidence=confidence,
            eligible_endorsements=len(in_edges),
            raw_support=support.quantize(Decimal("0.0001")),
            quality_factor=quality.quantize(Decimal("0.0001")),
        )

    @staticmethod
    def compute_reputation_update(
        old_reputation: Decimal,
        outcome_y: int,
        expected_p: Decimal = Decimal("0.90"),
        edge_weight: Decimal = Decimal("1.0"),
        evidence_reliability: Decimal = Decimal("1.0"),
        learning_rate: Decimal = Decimal("0.10"),
    ) -> Decimal:
        """Calculate outcome-conditioned reputation delta (Section 6.3 of Master Doc v2).

        error = y - p
        delta = learning_rate * edge_weight * error * evidence_reliability
        new_reputation = clamp(old_reputation + delta, 0, R_max)
        """
        error = Decimal(str(outcome_y)) - expected_p
        delta = learning_rate * edge_weight * error * evidence_reliability
        return max(Decimal("0.0"), old_reputation + delta).quantize(Decimal("0.01"))

    def assess_combined(
        self,
        borrower_id: str,
        loan_app: Optional[LoanApplication] = None,
        bureau_score: Optional[int] = None,
        bureau_status: BureauStatus = "NO_FILE",
    ) -> CombinedAssessment:
        """Produce the unblended side-by-side assessment (Section 8 of Master Doc v2)."""
        import uuid
        from veritrust.affordability import (
            AffordabilityEngine,
            affordability_input,
            affordability_status,
            calculate_emi,
        )

        user = self.engine.get_user(borrower_id)
        if not user:
            raise ValueError(f"Borrower '{borrower_id}' does not exist.")

        # 1. Bureau Signal
        bureau_report = BureauReport(
            status=bureau_status if bureau_score is None else "AVAILABLE",
            score=bureau_score,
            source="CIBIL" if bureau_score else None,
        )

        # 2. Vouch Signal
        vouch_report = self.compute_vouch_score(borrower_id)

        # 3. Affordability Signal
        fin = user.financial_features
        aff_input = affordability_input(fin)
        monthly_income = aff_input.monthly_income
        monthly_debt = aff_input.existing_debt_service
        aff_profile = AffordabilityEngine().evaluate(aff_input)

        # 4. Reason Codes & Factor Synthesis (Section 9 of Master Doc v2)
        positive_factors: list[dict] = []
        risk_factors: list[dict] = []
        missing_information: list[str] = []
        review_flags: list[str] = []

        if monthly_income > Decimal("0.0"):
            positive_factors.append({
                "code": "INCOME_PRESENT",
                "text": f"Verified recurring monthly income of INR {monthly_income:,.2f} documented",
                "source": "BANK_STATEMENT",
            })
        if fin and fin.income_volatility <= Decimal("0.15"):
            positive_factors.append({
                "code": "INCOME_STABLE",
                "text": f"Income volatility is low ({fin.income_volatility * 100:.1f}%), indicating predictable earnings",
                "source": "ACCOUNT_AGGREGATOR",
            })
        if vouch_report.eligible_endorsements > 0:
            positive_factors.append({
                "code": "COMMUNITY_VOUCH_ACTIVE",
                "text": f"Endorsed by {vouch_report.eligible_endorsements} active community member(s) with Vouch score {vouch_report.vouch_score}",
                "source": "WEB_OF_TRUST_GRAPH",
            })
        if aff_profile.disposable_income > Decimal("0.0"):
            positive_factors.append({
                "code": "DISPOSABLE_INCOME_SUFFICIENT",
                "text": f"Net disposable monthly surplus of INR {aff_profile.disposable_income:,.2f} after non-discretionary expenses and buffer",
                "source": "AFFORDABILITY_ENGINE",
            })

        if bureau_report.status == "NO_FILE":
            missing_information.append("Credit bureau history is unavailable on file (thin-file applicant)")
        elif bureau_score is not None and bureau_score < 650:
            risk_factors.append({
                "code": "BUREAU_SCORE_BELOW_PRIME",
                "text": f"Bureau score {bureau_score} is below prime threshold; investigating current cash-flow evidence",
                "source": "BUREAU_PULL",
            })

        if monthly_income > Decimal("0.0") and (monthly_debt / monthly_income) >= Decimal("0.40"):
            risk_factors.append({
                "code": "UTILIZATION_SPIKE",
                "text": f"High debt-service obligations ({monthly_debt / monthly_income * 100:.1f}% of income)",
                "source": "DEBT_RECORDS",
            })
            review_flags.append("OBLIGATION_SURGE_REVIEW")

        if fin and fin.completeness < Decimal("0.80"):
            missing_information.append("Living costs and cash-flow statements not fully documented")
            review_flags.append("DATA_COMPLETENESS_REVIEW")
        if fin is None:
            missing_information.append("No income or expense data shared yet: affordability is unknown, not poor")
        elif fin.net_operating_income <= Decimal("0.0"):
            missing_information.append("Operating costs not shared: a conservative INR 10,000 a month is assumed")

        if loan_app and aff_profile.max_affordable_emi > Decimal("0.0"):
            app_emi = calculate_emi(
                principal=loan_app.principal,
                annual_rate=loan_app.annual_rate,
                tenure_months=loan_app.term_months,
            )
            if app_emi > aff_profile.max_affordable_emi:
                risk_factors.append({
                    "code": "AFFORDABILITY_DEFICIT",
                    "text": f"Requested instalment of INR {app_emi:,.2f} exceeds affordable limit of INR {aff_profile.max_affordable_emi:,.2f}",
                    "source": "AFFORDABILITY_ENGINE",
                })
                review_flags.append("RESTRUCTURING_RECOMMENDED")

        aff_status = affordability_status(aff_profile.disposable_income)

        data_quality = "HIGH_CONFIDENCE_VERIFIED"
        if fin is None or fin.completeness < Decimal("0.50"):
            data_quality = "LOW"
        elif fin.completeness < Decimal("0.85") or bureau_report.status == "NO_FILE":
            data_quality = "MEDIUM"

        return CombinedAssessment(
            assessment_id=f"ASM_{uuid.uuid4().hex[:12].upper()}",
            application_id=loan_app.application_id if loan_app else None,
            borrower_id=borrower_id,
            bureau=bureau_report,
            vouch=vouch_report,
            affordability={
                "status": aff_status,
                "gross_monthly_income": str(aff_profile.monthly_income),
                "non_discretionary_outflows": str(aff_profile.total_non_discretionary),
                "disposable_income": str(aff_profile.disposable_income),
                "protected_cash_buffer": str(aff_profile.protected_buffer),
                "max_affordable_emi": str(aff_profile.max_affordable_emi),
                "binding_constraint": aff_profile.binding_policy_rule,
            },
            data_quality=data_quality,
            positive_factors=positive_factors,
            risk_factors=risk_factors,
            missing_information=missing_information,
            review_flags=review_flags,
            algorithm_version="vouch-v2.0",
        )


