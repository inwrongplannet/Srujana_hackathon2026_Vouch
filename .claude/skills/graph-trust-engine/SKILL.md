---
name: graph-trust-engine
description: Exact algorithm for trust path computation, vouch conservation, and cycle absorption in the web-of-trust graph
---
# graph-trust-engine

**Why this exists:** The trust graph math is subtle. A global visited-set, float intermediate products, or missed sibling re-weighting will silently produce wrong scores. This skill is the canonical reference.
**Used by:** Reehan, Abhijit
**Triggered by:** Any code that traverses the trust graph, reads or writes vouch weights, or computes a trust score

---

## When to use
Any implementation of: path traversal, vouch creation/deletion, trust aggregation, R_graph computation, or the graph evaluation service. Always read this before touching graph code.

---

## Core invariants (enforce all three; violation = bug)

### Invariant 1 — Out-Degree Conservation
```
C_u = max(0, R_u)
W_uv = C_u / |Out(u)|     for each v in Out(u)
sum(W_uv for v in Out(u)) <= C_u
```
- `C_u` is the total allocatable capacity of node `u`.
- Adding a new vouch from `u` **automatically dilutes all existing outgoing edges** from `u`. Re-derive all `W_uv` atomically — no partial updates.
- Removing a vouch re-derives all remaining siblings atomically.
- Nodes with `R_u <= 0` have `C_u = 0`; they cannot emit any positive vouch weight.

### Invariant 2 — Hop Attenuation
```
X = 0.5   (hop decay factor, fixed; log in DECISIONS.md if changed)
For path P = (v0, v1, ..., vk):
  Trust(P) = W_{v0,v1} * prod_{i=1}^{k-1} (W_{vi,vi+1} * X)
```
- `v0` must be an institutional anchor (root node with externally assigned R > 0).
- Trust attenuates geometrically with distance. A 3-hop path at full weight: `W * W*0.5 * W*0.25`.

### Invariant 3 — Cycle Absorption (visited-set is per-path, not global)
```
VP = set of nodes visited along the current path P so far
If the next candidate node v_{m+1} is in VP:
  Trust(P extended by v_{m+1}) = 0   -- absorbed, do not recurse further
```
- **Critical:** `VP` is reset for each new path enumeration. Do NOT share a global visited-set across paths.
- A cycle `A -> B -> C -> A` produces zero trust when re-entering A. It does not crash; it returns 0 and stops.
- Negative-score clusters (`R <= 0, C = 0`) produce zero weight on every outgoing edge; they are naturally absorbed without needing special handling.

---

## Algorithm: compute R_graph(T)

```python
def compute_r_graph(target: NodeId, anchors: set[NodeId], graph: Graph) -> Decimal:
    """
    Sum trust of all simple paths from any anchor to target.
    All arithmetic is Decimal. Never float.
    """
    total = Decimal("0")
    for anchor in anchors:
        for path_trust in enumerate_paths(anchor, target, graph, visited={anchor}, current_trust=Decimal("1")):
            total += path_trust
    return total

def enumerate_paths(
    current: NodeId,
    target: NodeId,
    graph: Graph,
    visited: set[NodeId],
    current_trust: Decimal,
) -> Iterator[Decimal]:
    if current == target:
        yield current_trust
        return
    for neighbor, weight in graph.out_edges(current):  # weight = W_{current, neighbor}
        if neighbor in visited:
            continue  # cycle absorption
        hop_trust = weight if current in anchors else weight * Decimal("0.5")
        # Note: the first hop (anchor -> v1) does not decay; decay starts at i=1
        yield from enumerate_paths(neighbor, target, graph, visited | {neighbor}, current_trust * hop_trust)
```

> Implementation note on the first hop: `Trust(P) = W_{v0,v1} * prod_{i=1}^{k-1}(W * X)`. The first edge `W_{v0,v1}` is NOT multiplied by X. X applies from i=1 onwards.

---

## Out-degree weight update (call this every time vouches change)

```python
def recompute_weights(node: NodeId, graph: Graph) -> None:
    """Must be called atomically inside a transaction/lock."""
    out_edges = graph.out_edges(node)
    n = len(out_edges)
    if n == 0:
        return
    c_u = max(Decimal("0"), graph.get_node(node).R_score)
    w = c_u / Decimal(n)
    for neighbor in out_edges:
        graph.set_edge_weight(node, neighbor, w)
```

---

## What to test (mandatory unit tests)

| Fixture | Expected result |
|---|---|
| Linear chain: anchor(R=10) -> A -> B. Compute R_graph(B). | `W_{anchor,A} * W_{A,B} * 0.5` = `(10/1) * (R_A/1) * 0.5` — verify numerically with known R_A |
| Triangle: anchor -> A -> B -> anchor (cycle). Compute R_graph(B). | Path via anchor->A->B only. Cycle anchor->A->B->anchor->... absorbed. No infinite loop. |
| Node with R=0 tries to vouch. | `C_u = 0`, `W_uv = 0` for all v. R_graph of vouched node = 0 from this path. |
| Two anchors, two paths to target. | R_graph = sum of both path trusts. |
| Add a third vouch from a node that has two existing vouches (R=9). | All three weights become 9/3 = 3, not the new one getting 4.5. |

---

## Common mistakes (do not repeat)

| Mistake | Why it's wrong |
|---|---|
| Global visited-set shared across all paths | Makes cycles in one path cancel valid paths from other routes |
| `float` for weight or trust products | Floating-point drift silently changes scores; use `Decimal` |
| Updating only the new edge weight, not siblings | Violates out-degree conservation; sums exceed C_u |
| Applying X to the first hop (anchor -> v1) | The formula starts the prod at i=1, not i=0 |
| Returning 0 for the whole graph when one path cycles | Cycle absorption returns 0 for that path only, not the whole computation |
