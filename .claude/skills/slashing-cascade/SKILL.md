---
name: slashing-cascade
description: Exact 4-level default penalty cascade, atomicity rules, and circuit-breaker logic for the trust graph
---
# slashing-cascade

**Why this exists:** Inventing intermediate penalty fractions or applying slashes sequentially (non-atomically) produces inconsistent graph state. This skill is the single source of truth.
**Used by:** Reehan, Abhijit
**Triggered by:** Any default event, slash computation, or circuit-breaker check

---

## When to use
Any implementation of: default trigger handling, slash execution, cascade propagation, or the circuit-breaker pause mechanism.

---

## The 4-level cascade (exact fractions — do not deviate)

| Distance from defaulter | Who | Penalty |
|---|---|---|
| `k = 0` | Defaulter `B` themselves | Full slash: `R_B <- R_B - delta0`; state -> `DEFAULTED`; all outbound capacity frozen (`C_B = 0`) |
| `k = 1` | Direct sponsor `A` (vouched for `B`) | `delta_A = gamma * W_AB * delta0` where `gamma = 0.5` |
| `k = 2` | Transitive ancestor (vouched for `A`) | `delta = gamma^2 * delta0 = 0.25 * delta0` |
| `k >= 3` | All other nodes | `delta = 0` — hard cutoff, no propagation |

```
gamma = 0.5   (fixed; log in DECISIONS.md if changed)
delta0 = the primary slash amount (set per loan, typically proportional to loan size)
```

**Example with delta0 = 10:**
- Defaulter B: R drops by 10.0
- Direct sponsor A (W_AB = 0.4): drops by `0.5 * 0.4 * 10 = 2.0`
- Transitive ancestor: drops by `0.25 * 10 = 2.5`
- Everyone else: unchanged

---

## Atomicity rule

All slash operations for a single default event **must be applied in a single atomic transaction** (one DB transaction, one in-memory lock). Steps:

1. Collect all affected nodes (k=0, k=1, k=2) and their penalty amounts.
2. Apply all R updates at once.
3. Recompute all affected C_u and W_uv values (use `graph-trust-engine` skill: `recompute_weights`).
4. Update state flags (`DEFAULTED`, `RESTRICTED`) in the same transaction.
5. Commit or rollback atomically.

Never apply k=0, then k=1, then k=2 as separate operations — intermediate states must not be observable.

---

## State transitions on default

```
Defaulter B:   ACTIVE -> DEFAULTED
  R_B <- R_B - delta0
  C_B = 0  (capacity frozen)
  All outbound vouch weights set to 0

k=1 sponsor A: ACTIVE -> RESTRICTED  (if R_A drops below 0 after penalty)
               ACTIVE -> ACTIVE       (if R_A remains positive)
  R_A <- R_A - delta_A
  Recompute W_Av for all v in Out(A)

k=2 ancestor:  Same state logic as k=1 applied to ancestor
```

---

## Circuit-breaker (localised shock protection)

When a geographic or sector cluster experiences simultaneous defaults, automated slashing is paused:

```
theta = 0.3   (default rate threshold; 30% of a cluster defaulting simultaneously)

cluster_default_rate = count(DEFAULTED nodes in cluster) / count(all nodes in cluster)

if cluster_default_rate > theta:
    pause_automated_slashing(cluster_id)
    flag_for_manual_review(cluster_id, reason="force_majeure_suspected")
```

During a circuit-breaker pause:
- New defaults are recorded but slashes are queued, not applied.
- Sponsors are NOT penalised until the review resolves.
- A manual `resume_slashing(cluster_id)` or `restructure(cluster_id)` call is required to close the pause.

Cluster definition: nodes linked by geography tag or sector tag in seed data. For the demo, hardcode 2-3 clusters.

---

## Required unit tests

| Case | Assertion |
|---|---|
| Single default, one direct sponsor | R_B reduced by delta0; R_A reduced by `0.5 * W_AB * delta0`; R of k=2 ancestor reduced by `0.25 * delta0`; k=3 node unchanged |
| Atomic application | Intermediate state (only k=0 applied, not k=1 yet) must never be readable |
| Circuit breaker fires | When 3 of 5 nodes in a cluster default simultaneously, slashes for the 3rd default are queued, not applied |
| Node with R already at 0 gets slashed | R_B goes negative; C_B stays 0; no error |
| DEFAULTED node's sponsor tries to vouch for a new node | Vouch is rejected if C_sponsor = 0 (sponsor was also slashed to 0) |

---

## Common mistakes (do not repeat)

| Mistake | Why it's wrong |
|---|---|
| Sequential slash (k=0 committed, then k=1 committed separately) | A crash between steps leaves inconsistent graph state |
| Applying k=3 penalty anyway "for safety" | Violates the contagion isolation guarantee — judges will ask about this |
| Recalculating W_uv before all R values are updated | Other threads may read stale weights during the cascade |
| Forgetting to recompute sibling weights after C changes | Out-degree conservation violated |
