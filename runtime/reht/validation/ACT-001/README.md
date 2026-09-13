# Case 01 — ACT-001 independent execution authorization

This validation package consumes the fixed `AS-001` v0.2.2 authority-state
contract and invokes the canonical `valo_reht.RealReht` runtime. It does not
reconstruct Authority State and it does not infer missing identity, authority,
premise acceptance, or constraints.

The interface mapping is intentionally fail-closed:

- `AUTH-001` remains immutable historical evidence and is not placed in the
  runtime `authority` collection.
- `IDENTITY_NOT_VERIFIED` maps to a missing verified execution identity.
- `INSUFFICIENT / NON_OPERATIVE` maps to no current operative authority.
- both unresolved constraints remain required on the exact action contract.
- the complete incoming evidence lineage is preserved unchanged.

Expected Case 01 result:

```text
RealReht -> DENY
reason   -> no verified execution identity
clearance_ref -> null
permit_ref    -> null
effect commit -> prohibited
```

The additional identity-only negative test proves the next independent guard:
even if identity were supplied, an empty current-authority set still returns
`DENY`, not `STEP_UP` or `ALLOW`.

Run locally after installing the pinned Workflow ISA dependency and this
package:

```bash
python validation/ACT-001/generate_act001.py \
  --authorization-instant 2026-08-21T20:00:00Z
python validation/ACT-001/validate_act001.py
python -m pytest -q tests/test_act001_case01.py
```

The GitHub Actions workflow uses a real wall-clock authorization instant,
records the exact checked-out implementation commit, independently replays the
runtime decision, runs the negative suite, and uploads a SHA-256-bound evidence
package. No downstream effect is executed.
