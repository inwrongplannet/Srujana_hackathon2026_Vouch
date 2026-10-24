# VeriTrust — Technical Architecture (Engine POC)

Scope: A standalone credit-assessment engine that takes a trust graph and simulated financial data, calculates reputation and trust, and produces an explainable credit assessment.

No ZK, blockchain, smart contracts, frontend, or real identity verification.

## 1. System architecture

\#chatgpt-mermaid-\_r_n2\_{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica,Apple Color Emoji,Arial,sans-serif,Segoe UI Emoji,Segoe UI Symbol;font-size:16px;fill:rgb(237, 237, 237);}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#chatgpt-mermaid-\_r_n2\_ .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_n2\_ .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_n2\_ .error-icon{fill:rgb(48, 48, 48);}#chatgpt-mermaid-\_r_n2\_ .error-text{fill:rgb(237, 237, 237);stroke:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_n2\_ .edge-thickness-normal{stroke-width:1px;}#chatgpt-mermaid-\_r_n2\_ .edge-thickness-thick{stroke-width:3.5px;}#chatgpt-mermaid-\_r_n2\_ .edge-pattern-solid{stroke-dasharray:0;}#chatgpt-mermaid-\_r_n2\_ .edge-thickness-invisible{stroke-width:0;fill:none;}#chatgpt-mermaid-\_r_n2\_ .edge-pattern-dashed{stroke-dasharray:3;}#chatgpt-mermaid-\_r_n2\_ .edge-pattern-dotted{stroke-dasharray:2;}#chatgpt-mermaid-\_r_n2\_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_n2\_ .marker.cross{stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_n2\_ svg{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica,Apple Color Emoji,Arial,sans-serif,Segoe UI Emoji,Segoe UI Symbol;font-size:16px;}#chatgpt-mermaid-\_r_n2\_ p{margin:0;}#chatgpt-mermaid-\_r_n2\_ .label{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica,Apple Color Emoji,Arial,sans-serif,Segoe UI Emoji,Segoe UI Symbol;color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_n2\_ .cluster-label text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_n2\_ .cluster-label span{color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_n2\_ .cluster-label span p{background-color:transparent;}#chatgpt-mermaid-\_r_n2\_ .label text,#chatgpt-mermaid-\_r_n2\_ span{fill:rgb(237, 237, 237);color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_n2\_ .node rect,#chatgpt-mermaid-\_r_n2\_ .node circle,#chatgpt-mermaid-\_r_n2\_ .node ellipse,#chatgpt-mermaid-\_r_n2\_ .node polygon,#chatgpt-mermaid-\_r_n2\_ .node path{fill:rgb(9, 23, 44);stroke:rgb(31, 78, 148);stroke-width:1px;}#chatgpt-mermaid-\_r_n2\_ .rough-node .label text,#chatgpt-mermaid-\_r_n2\_ .node .label text,#chatgpt-mermaid-\_r_n2\_ .image-shape .label,#chatgpt-mermaid-\_r_n2\_ .icon-shape .label{text-anchor:middle;}#chatgpt-mermaid-\_r_n2\_ .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#chatgpt-mermaid-\_r_n2\_ .rough-node .label,#chatgpt-mermaid-\_r_n2\_ .node .label,#chatgpt-mermaid-\_r_n2\_ .image-shape .label,#chatgpt-mermaid-\_r_n2\_ .icon-shape .label{text-align:center;}#chatgpt-mermaid-\_r_n2\_ .node.clickable{cursor:pointer;}#chatgpt-mermaid-\_r_n2\_ .root .anchor path{fill:rgb(175, 175, 175)!important;stroke-width:0;stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_n2\_ .arrowheadPath{fill:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_n2\_ .edgePath .path{stroke:rgb(175, 175, 175);stroke-width:1px;}#chatgpt-mermaid-\_r_n2\_ .flowchart-link{stroke:rgb(175, 175, 175);fill:none;}#chatgpt-mermaid-\_r_n2\_ .edgeLabel{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-\_r_n2\_ .edgeLabel p{background-color:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_n2\_ .edgeLabel rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_n2\_ .labelBkg{background-color:rgba(0, 0, 0, 0.5);}#chatgpt-mermaid-\_r_n2\_ .cluster rect{fill:rgb(48, 48, 48);stroke:rgba(255, 255, 255, 0.15);stroke-width:1px;}#chatgpt-mermaid-\_r_n2\_ .cluster text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_n2\_ .cluster span{color:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_n2\_ div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica,Apple Color Emoji,Arial,sans-serif,Segoe UI Emoji,Segoe UI Symbol;font-size:12px;background:rgb(48, 48, 48);border:1px solid rgba(255, 255, 255, 0.15);border-radius:2px;pointer-events:none;z-index:100;}#chatgpt-mermaid-\_r_n2\_ .flowchartTitleText{text-anchor:middle;font-size:18px;fill:rgb(237, 237, 237);}#chatgpt-mermaid-\_r_n2\_ rect.text{fill:none;stroke-width:0;}#chatgpt-mermaid-\_r_n2\_ .icon-shape,#chatgpt-mermaid-\_r_n2\_ .image-shape{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-\_r_n2\_ .icon-shape p,#chatgpt-mermaid-\_r_n2\_ .image-shape p{background-color:rgb(0, 0, 0);padding:2px;}#chatgpt-mermaid-\_r_n2\_ .icon-shape .label rect,#chatgpt-mermaid-\_r_n2\_ .image-shape .label rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-\_r_n2\_ .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#chatgpt-mermaid-\_r_n2\_ .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#chatgpt-mermaid-\_r_n2\_ .node .neo-node{stroke:rgb(31, 78, 148);}#chatgpt-mermaid-\_r_n2\_ [data-look="neo"].node rect,#chatgpt-mermaid-\_r_n2\_ [data-look="neo"].cluster rect,#chatgpt-mermaid-\_r_n2\_ [data-look="neo"].node polygon{stroke:url(#chatgpt-mermaid-\_r_n2\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_n2\_ [data-look="neo"].swimlane.cluster rect{filter:none;}#chatgpt-mermaid-\_r_n2\_ [data-look="neo"].node path{stroke:url(#chatgpt-mermaid-\_r_n2\_-gradient);stroke-width:1px;}#chatgpt-mermaid-\_r_n2\_ [data-look="neo"].node .outer-path{filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_n2\_ [data-look="neo"].node .neo-line path{stroke:rgb(31, 78, 148);filter:none;}#chatgpt-mermaid-\_r_n2\_ [data-look="neo"].node circle{stroke:url(#chatgpt-mermaid-\_r_n2\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_n2\_ [data-look="neo"].node circle .state-start{fill:#000000;}#chatgpt-mermaid-\_r_n2\_ [data-look="neo"].icon-shape .icon{fill:url(#chatgpt-mermaid-\_r_n2\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_n2\_ [data-look="neo"].icon-shape .icon-neo path{stroke:url(#chatgpt-mermaid-\_r_n2\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_n2\_ .node text{font-size:14px;font-weight:600;letter-spacing:normal;fill:rgb(153, 206, 255);}#chatgpt-mermaid-\_r_n2\_ .edgeLabels text{font-size:13px;font-weight:600;letter-spacing:-0.08px;fill:rgb(153, 206, 255);}#chatgpt-mermaid-\_r_n2\_ .node tspan[font-weight="normal"],#chatgpt-mermaid-\_r_n2\_ .edgeLabels tspan[font-weight="normal"]{font-weight:600;}#chatgpt-mermaid-\_r_n2\_ .edgeLabel .label rect{opacity:1;rx:13px;ry:13px;fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-width:1px;}#chatgpt-mermaid-\_r_n2\_ .node rect,#chatgpt-mermaid-\_r_n2\_ .node circle,#chatgpt-mermaid-\_r_n2\_ .node ellipse,#chatgpt-mermaid-\_r_n2\_ .node polygon,#chatgpt-mermaid-\_r_n2\_ .node path{fill:rgb(0, 40, 77);stroke:rgba(255, 255, 255, 0.1);stroke-width:1px;}#chatgpt-mermaid-\_r_n2\_ .node rect{rx:16px;ry:16px;}#chatgpt-mermaid-\_r_n2\_ .node.mermaid-decision .label-container{fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-dasharray:2px,2px;}#chatgpt-mermaid-\_r_n2\_ .edgePaths .flowchart-link{stroke:rgb(175, 175, 175);stroke-width:1px;stroke-linecap:round;stroke-linejoin:round;}#chatgpt-mermaid-\_r_n2\_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-\_r_n2\_ :root{--mermaid-font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,Segoe UI,Helvetica,Apple Color Emoji,Arial,sans-serif,Segoe UI Emoji,Segoe UI Symbol;}JSON / CSV Sample DataData Loader and ValidatorGraph BuilderTrust Propagation EngineReputation EngineSimulated Financial FeaturesCredit Assessment EngineDecision and ExplanationEngineJSON Results / CLI OutputSimulated Loan Events

## 2. Technical components

| Module               | Responsibility                                                                      | Output                                     |
| -------------------- | ----------------------------------------------------------------------------------- | ------------------------------------------ |
| `data_loader`        | Load and validate users, vouches, financial features, and loan events.              | Validated records                          |
| `graph_builder`      | Construct a directed graph of participants and endorsements.                        | Trust graph                                |
| `trust_engine`       | Calculate vouch weights, propagate trust, apply hop decay, and reject cyclic paths. | Trust scores and contributing paths        |
| `reputation_engine`  | Process repayments, defaults, rewards, and sponsor penalties.                       | Updated reputation                         |
| `credit_engine`      | Combine trust, repayment capacity, and uncertainty.                                 | Credit assessment                          |
| `explanation_engine` | Explain score contributions, uncertainty, and risk factors.                         | Assessment report                          |
| `simulation`         | Generate loan events and test different graph scenarios.                            | Updated graph state and evaluation results |

## 3. Suggested technology stack

Keep the stack small enough to finish in six hours.

| Layer                  | Technology                             |
| ---------------------- | -------------------------------------- |
| Language               | Python                                 |
| Graph representation   | NetworkX                               |
| Data validation        | Pydantic                               |
| Numerical calculations | NumPy                                  |
| Input data             | JSON / CSV                             |
| Interface              | CLI initially; FastAPI if time permits |
| Testing                | pytest                                 |
| Persistence            | In-memory initially                    |

NetworkX handles graph traversal and cycle-related operations. Your trust formulas and reputation rules should remain custom code rather than being hidden inside a graph library.

## 4. Internal data flow

### A. Graph construction

Represent users as nodes and vouches as directed edges.

```json
user = {    "user_id": "U001",    "reputation": 10.0,    "financial_features": {        "monthly_income": 25000,        "monthly_debt": 5000,        "income_volatility": 0.15    }}vouch = {    "source": "U001",    "target": "U002",    "active": True}
```

The example values are synthetic. The graph should store protocol identifiers rather than sensitive identity information.

### B. Trust propagation

For each borrower:

1. Find paths from trusted root nodes.
2. Calculate available vouch capacity.
3. Assign edge weights.
4. Apply hop attenuation.
5. Prevent repeated nodes within a path from contributing additional trust.
6. Aggregate the valid path contributions.

Use a configurable decay factor, initially \\(\lambda=0.5\\).

### C. Reputation updates

The reputation engine consumes simulated events:

```text
LOAN_REPAID
    → Increase borrower reputation
    → Apply sponsor reward
    → Recalculate affected trust

LOAN_DEFAULTED
    → Penalize borrower
    → Penalize direct sponsors
    → Apply damped second-hop penalties
    → Recalculate affected trust
```

Events must be processed only once. Otherwise, replaying the same repayment event could inflate reputation.

### D. Credit assessment

The credit engine combines:

- Graph-derived trust.
- Estimated repayment capacity.
- Epistemic uncertainty — uncertainty caused by limited information.

The proposed decision rule from your document is:

\\[ S\_{\text{final}}=\mu\_{\text{composite}}-\kappa\sigma\_{\text{epistemic}} \\]

The financial model and uncertainty calculation still need to be defined. For the POC, use explicit synthetic-data rules and label the resulting limit as a prototype recommendation, not a validated lending decision.

## 5. Suggested project structure

```text
veritrust-engine/
├── data/
│   ├── users.json
│   ├── vouches.json
│   └── loan_events.json
├── src/
│   └── veritrust/
│       ├── data_loader.py
│       ├── graph_builder.py
│       ├── trust_engine.py
│       ├── reputation_engine.py
│       ├── credit_engine.py
│       ├── explanation_engine.py
│       └── simulation.py
├── tests/
│   ├── test_trust.py
│   ├── test_cycles.py
│   ├── test_reputation.py
│   └── test_credit.py
├── main.py
├── requirements.txt
└── README.md
```

## 6. Six-hour implementation order

Hour 1 — Data and graph

Define schemas, load sample data, construct the graph.

Hours 2–3 — Trust engine

Implement capacity conservation, path scoring, hop decay, and cycle prevention.

Hour 4 — Reputation

Implement repayment and default events, sponsor penalties, and duplicate-event protection.

Hour 5 — Credit assessment

Combine trust, financial features, uncertainty, and explanations.

Hour 6 — Testing

Test collusion, disconnected users, repeated events, defaults, and changing reputation.

The main engineering priority is `trust_engine.py`. Keep it deterministic, independently testable, and separate from the credit model. That lets you change the financial scoring approach later without rewriting the trust protocol.