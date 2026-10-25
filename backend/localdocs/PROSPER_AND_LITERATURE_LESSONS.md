# How Prosper & Credit Literature Relate to VeriTrust: Empirical Lessons, Cheap-Talk Failure Modes, and Anti-Herding Design

**Status:** Technical specification and literature benchmark document.  
**Research References:**
- *The Information Value of Online Social Networks: Lessons from Peer-to-Peer Lending* (Freedman & Jin, 2017; Lin, Prabhala & Viswanathan, *Management Science* 2013).
- *Rational Herding in Microloan Markets* (Zhang & Liu, *Management Science* 2012).
- *Invisible Primes: Fintech Lending with Alternative Data* (Di Maggio & Ratnadiwakara, *Management Science* 2026).
- *Network Centrality and Credit Risk* (*Finance Research Letters* 2024).
- *DeepCredit: Exploiting User Clickstream for Loan Risk Prediction* (Yang et al., *AAAI ICWSM* 2018).
- *A Holistic Approach to Interpretability in Financial Lending* (*Decision Support Systems* 2022).
- *Signals from SMS: Alternative Data in Credit Scoring* (Lee, Ryu & Shin, 2026).
- *Drift-Aware and Explainable Credit Scoring* (Mani et al., *Complex & Intelligent Systems* 2026).
- Empirical verification on **55,305 resolved Prosper loans** from `data/combined/prosper_loans.csv`.

---

## 1. Executive Summary & The Prosper Precedent

Prosper Marketplace connects borrowers and investors and provides a foundational real-world precedent for social lending. Between 2005 and 2014, Prosper allowed borrowers to display friends' recommendations, group affiliations, and social networks to peer lenders.

Prosper's experience demonstrates a critical lesson: **visible social endorsements influenced lenders to fund loans at lower rates, but unbacked endorsements completely failed to improve repayment outcomes.**

### Empirical Evidence from 55,305 Resolved Prosper Loans

We evaluated the complete Prosper loan dataset (`prosper_loans.csv`) to test the relationship between **cheap-talk recommendations** (unbacked text endorsements) vs. **friends who invested capital** (financial skin-in-the-game):

| Borrower Endorsement Category | Resolved Loans ($n$) | Actual Default Rate | Default Rate vs. Platform Baseline (30.79%) | Finding |
|---|---|---|---|---|
| **Platform Baseline** (All Resolved Loans) | 55,305 | **30.79%** | — | Overall population benchmark |
| **No Endorsements & No Friends Invested** | 50,000 | **30.98%** | $+0.19\%$ | Standard impersonal loans |
| **Pure Cheap-Talk Recommendations** (`recommendations > 0`, ZERO money invested) | 2,182 | **32.81%** | **$+2.02\%$ (Worse Risk!)** | **Adverse Selection / Predatory Cheap Talk** |
| **Endorsements WITH Money Invested** (`recommendations > 0` + `friends_invested > 0`) | 1,623 | **25.45%** | **$-5.34\%$ (Lower Risk)** | **Genuine Social Collateral** |
| **Any Friends Invested** (`friends_invested_count > 0`) | 2,016 | **23.71%** | **$-7.08\%$ (Best Repayment)** | **Strongest Predictive Signal** |

> **The Cheap-Talk Trap:** In Prosper's data, borrowers who obtained social recommendations with **zero money invested defaulted at 32.81%—a HIGHER default rate than the platform average (30.79%)!** 
> Desperate or subprime borrowers solicited unbacked verbal endorsements to dress up their profiles. Only when friends put their own capital on the line did the default rate plummet to **23.71%**.

---

## 2. Comparing Systems: Prosper vs. VeriTrust

| Dimension | Prosper Marketplace (Historical) | VeriTrust Protocol (Proposed) |
|---|---|---|
| **Core Architecture** | P2P lending marketplace & loan originator | Decentralized credibility & reputation layer for any lender |
| **Endorsement Mechanism** | Unverified text testimonials ("Recommendations") | Cryptographically signed vouches with allocated reputation |
| **Endorser Liability** | **Zero liability**; free cheap talk | **Reputational Slashing**: endorser loses $q_u \cdot R_u$ on borrower default |
| **Allocation Conservation** | Infinite: a user could endorse hundreds of friends with no dilution | **Strict Conservation**: $\sum_{v} w_{uv} = R_u$; allocation splits as $R_u / d_u$ |
| **Propagation** | 1-hop only: visible badge on listing page | **Multi-hop Web-of-Trust**: $T(P) = R_s \prod \frac{1}{d_v} \prod \alpha \delta^{h-1}$ |
| **Temporal Weighting** | None: all recommendations displayed chronologically | **Chronological Rank Discounting**: $\alpha_{uv} = 1/2^{r_{uv}-1}$ |
| **Sybil Resistance** | Phone verification only | Cycle absorption, min-path provenance, anchor trust seeds |

---

## 3. Four Core Prosper Lessons for VeriTrust

### Lesson A: An Endorsement Without Cost is Worse Than No Endorsement
Prosper proves that unbacked endorsements introduce **adverse selection**. Lenders saw endorsements and lowered interest rates, but the borrowers actually defaulted at a higher rate ($32.81\%$).
- **How VeriTrust Fixes This:**
  1. **Slashing Cascade**: An endorsement allocates real owned reputation ($w_{uv} = R_u / d_u$). When borrower $D$ defaults with severity $S_D$, endorsers suffer an atomic penalty:
     $$\Delta_u = q_u \cdot R_u, \quad q_u = \eta \cdot S_D \cdot \frac{w_{uD}}{R_u}$$
  2. **Pre-Application Financial Support**: In our ablation study on 4,502 shock borrowers, pre-application liquidity support (`support_before_application_minor`)—the exact counterpart to Prosper's `friends_invested`—was required to maintain Brier score calibration ($0.1190$).

### Lesson B: Herding and Feedback Loops (*Zhang & Liu, Management Science 2012*)
Zhang and Liu showed that lenders engage in "rational herding": listings that gain initial funding momentum attract disproportionate subsequent capital, regardless of underlying fundamentals.
- **The VeriTrust Danger:** If an applicant's current graph score ($G_{\text{score}}$) is publicly displayed, peers may rush to endorse them simply because they are already high-scoring, creating a self-reinforcing credibility bubble.
- **VeriTrust Safeguards:**
  1. **Score-Blind Allocation**: Outgoing endorsement weights are determined strictly by the endorser's owned reputation $R_u$ and outgoing degree $d_u$, **never by the recipient's existing score**.
  2. **Fixed Provenance Min-Path**: Multiple paths from the same root source are collapsed via $p_u(s) = \min_{P} T(P)$, so a herding cluster cannot artificially inflate credibility.

### Lesson C: The Early-Endorsement Threat Model
Prosper's herding findings reveal a critical vulnerability in chronological weighting:
- VeriTrust's rule, $\alpha_i = 1/2^{i-1}$, severely attenuates late endorsements (rank 5 gets weight $1/16$).
- **The Attack Vector:** A coordinated syndicate can pre-arrange to place collusive endorsements **early** (capturing ranks 1 and 2 with weights $1.0$ and $0.5$) before honest community members vouch.
- **VeriTrust Safeguards:**
  1. **Anchor Vetting & Source Reputation**: Chronological rank is an attenuation multiplier, not an automatic entry pass:
     $$T(P) = R_s \cdot \left(\frac{1}{d_s}\right) \cdot \alpha_{s, v_1} \cdot \delta^{0}$$
     If source $s$ has near-zero owned reputation ($R_s \approx 0$) or zero anchor path, even a rank-1 endorsement contributes zero credibility.
  2. **Reciprocal Collusion Damping**: Mutual loops ($u \leftrightarrow v$) trigger cycle absorption and path nullification.

### Lesson D: Combining Hybrid Signals (Prosper Score + Bureau)
Prosper's SEC filings note that their proprietary Prosper Score is only predictive when evaluated **jointly** with credit bureau tradelines.
- **VeriTrust Alignment:** Our ablation study confirmed this exact principle:
  - Model A (Bureau Only): AUC $0.8841$
  - Model D (Bureau + Full VeriTrust): AUC **$0.8892$** (PR-AUC **$0.9191$**, Brier **$0.1190$**)
  - Model E3 (Graph Only, No Bureau): AUC $0.8678$
  - **Verdict:** VeriTrust is not designed to replace financial data; it is an orthogonal credibility layer that rescues creditworthy borrowers ("Invisible Primes") during adverse shocks.

---

## 4. Empirical Ablation Results & The "Invisible Primes" Proof

In our 6-level empirical ablation study ([`backend/ml/ablation.py`](../ml/ablation.py)), we evaluated:

1. **Topology vs Trust**:
   - Model A (Financial & Bureau baseline): AUC **0.8841**, Brier **0.1204**.
   - Model B (A + Degree Centrality): AUC **0.8842**, Brier **0.1228**.
   - **Result:** Degree centrality produced a statistically insignificant delta ($\Delta\text{AUC} = +0.0001$, $95\%$ CI: $[-0.0109, +0.0101]$).
2. **Quality & Mathematical Propagation**:
   - Model D (Full VeriTrust): XGBoost GPU AUC **0.8888** (PR-AUC **0.9273**), LightGBM AUC **0.8901**, Generalized Ensemble AUC **0.8892** (Brier **0.1190**, KS **0.6655**).
3. **Invisible Primes Unlocked**:
   - VeriTrust unlocked **26 borrowers** (4.18% of conventional rejections).
   - Unlocked borrowers defaulted at **38.46%**, compared to the general population default rate of **64.71%** (a **26.25% lower default rate**).
4. **Thin-File Cold Start**:
   - Model E3 (Graph collateral alone without any bureau data) achieved an AUC of **0.8678** and PR-AUC of **0.9002**.
