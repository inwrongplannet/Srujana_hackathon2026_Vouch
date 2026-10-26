<!-- Why: a tiny, uniform record per feature that tooling can read. -->
# Feature: Community
- **Assignee:** Reehan
- **Status:** in-progress
- **One-liner:** Hybrid vouching platform: borrowers post an ask and choose what strangers may see; anyone can vouch, always staking the same platform-set 15 reputation points (no stake slider), as someone who knows them (KNOWN) or as a stranger who read their verified summary (EVIDENCE, weighted by the voucher's track record and capped); vouchers stand by or step back after a setback; live on `/api/v1/community` when the backend answers (vouches, previews, stand-by and what strangers see all go to the server), demo data when it does not, with a badge saying which; every figure with a dotted label opens the formula behind it, its terms and the file that computes it (`src/features/explain/formulas.ts`)
