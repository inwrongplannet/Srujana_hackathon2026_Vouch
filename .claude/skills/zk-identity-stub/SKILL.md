---
name: zk-identity-stub
description: ZK nullifier design, demo stub implementation, node state machine, and anti-churn guarantees
---
# zk-identity-stub

**Why this exists:** The real system uses a Poseidon ZK circuit. For the hackathon demo, we use a sha256-based stub. The stub must be clearly labelled, deterministic, and must never be presented as a real zero-knowledge proof.
**Used by:** Reehan, Abhijit
**Triggered by:** Any identity registration, nullifier computation, duplicate-identity check, or node state transition

---

## When to use
Any implementation of: identity onboarding, nullifier generation, IdentityRegistry, duplicate rejection, or node state machine transitions.

---

## What the real system does (for reference only — not for the demo)

```
sk (identity secret) = Poseidon(Aadhaar_raw, Salt_user)
Nullifier            = Poseidon(sk, Protocol_Salt)
```

Verified via a Circom/Groth16 zero-knowledge proof. The nullifier is public; the Aadhaar is never revealed. Groth16 ensures the prover knows the preimage without disclosing it.

---

## What the demo stub does (implement this)

```python
import hashlib, os

PROTOCOL_SALT = os.environ["POSEIDON_PROTOCOL_SALT"]  # set in .env, never hardcoded

def compute_nullifier_stub(raw_id: str, user_salt: str) -> str:
    """
    # ZK_STUB: sha256-based mock of Poseidon(Poseidon(raw_id, user_salt), PROTOCOL_SALT)
    # NOT a real zero-knowledge proof. Replace with Circom circuit before production.
    """
    sk = hashlib.sha256(f"{raw_id}:{user_salt}".encode()).hexdigest()
    nullifier = hashlib.sha256(f"{sk}:{PROTOCOL_SALT}".encode()).hexdigest()
    return nullifier
```

**Rules for the stub:**
- Every function, comment, and UI label that touches this code must include `# ZK_STUB` (code) or "simulated identity anchor" (UI copy). Never write "zero-knowledge proof" in UI text for the stub path.
- `PROTOCOL_SALT` comes from the environment (`POSEIDON_PROTOCOL_SALT` in `.env.example`). It is never hardcoded or logged.
- The stub is deterministic: same `raw_id` + `user_salt` always produces the same nullifier, even across restarts.
- For demo data, `user_salt` is a fixed per-node value stored in `data/nodes.json` as `salt_stub`. Never use real Aadhaar/PAN; use obviously fake IDs like `DEMO0001`, `DEMO0002`.

---

## Node state machine

```
UNREGISTERED
    |
    | register(nullifier)  -- rejected if nullifier already exists
    v
  ACTIVE
    |              \
    | default       | vouch (once R > 0)
    v               v
DEFAULTED        (can vouch for others)
    |
    | (nullifier is permanent; re-registering same raw_id -> same DEFAULTED nullifier)
    v
DEFAULTED (permanent until manual governance override)

ACTIVE -> RESTRICTED: when R drops below 0 due to a k=1 slash (not a primary default)
RESTRICTED -> ACTIVE: when R recovers above 0 (e.g. via new settlements or governance)
```

### Transition rules

| Transition | Trigger | Guard |
|---|---|---|
| UNREGISTERED -> ACTIVE | `register(nullifier)` | Nullifier not already in registry |
| ACTIVE -> DEFAULTED | Default event on a loan held by this node | Grace period expired, LoanEscrow signals |
| ACTIVE -> RESTRICTED | Slash drops R below 0 (k=1 or k=2 penalty) | R < 0 after slash |
| RESTRICTED -> ACTIVE | R recovers above 0 | R > 0 after a settlement credit |
| Any -> DEFAULTED | Primary slash (k=0) | Overrides RESTRICTED |
| DEFAULTED -> ACTIVE | Manual governance only | Not automated; requires admin flag |

---

## Anti-churn guarantee (key property to demo to judges)

A defaulted borrower **cannot escape their history** by creating a new wallet:

```
Same raw_id + same user_salt -> same nullifier -> same DEFAULTED record in IdentityRegistry
```

For the stub, `user_salt` is stored in the demo node record. In the real system, `user_salt` is derived from the user's private key — they can't change it without losing access to their existing wallet, which is also blocked.

This must be demonstrated in the demo: "Even if a defaulter abandons their wallet, re-registering produces the same blocked identity."

---

## IdentityRegistry interface

```python
class IdentityRegistry:
    def register(self, nullifier: str) -> Node:
        """Raises DuplicateIdentityError if nullifier exists."""

    def get_node(self, nullifier: str) -> Node | None:
        """Returns None if not registered."""

    def get_status(self, nullifier: str) -> Literal["ACTIVE", "RESTRICTED", "DEFAULTED"] | None:

    def set_status(self, nullifier: str, status: str) -> None:
        """Called by VouchHub/LoanEscrow on slash or settlement. Never called by user input."""
```

For the demo, back this with SQLite or an in-memory dict. No live EVM required.

---

## .env.example entries to add

```
POSEIDON_PROTOCOL_SALT=  # required; any long random string; shared across all nodes in the demo cluster
DEMO_MODE=true           # when true, skip real ZK proof verification; use stub
```

---

## Required unit tests

| Test | Assertion |
|---|---|
| Same raw_id + salt produces same nullifier | `compute_nullifier_stub("DEMO0001", "abc") == compute_nullifier_stub("DEMO0001", "abc")` |
| Different raw_id produces different nullifier | `compute_nullifier_stub("DEMO0001", "abc") != compute_nullifier_stub("DEMO0002", "abc")` |
| Duplicate registration rejected | Second `register(same_nullifier)` raises `DuplicateIdentityError` |
| DEFAULTED state is sticky | `set_status(nullifier, "DEFAULTED")` then `set_status(nullifier, "ACTIVE")` is rejected (requires governance flag) |
| PROTOCOL_SALT affects nullifier | Changing env salt changes nullifier output |
