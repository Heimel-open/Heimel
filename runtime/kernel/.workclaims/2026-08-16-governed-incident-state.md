# Work claim — Governed incident state

- Active delivery: deterministic Kernel incident lifecycle state with append-only event transitions.
- Repository: `nsolland/valo-kernel`
- Canonical base SHA: `a58ed4bab15ff9383911c0bc6d0425c6362cd532`
- Branch: `feat/governed-incident-state`
- Owner/claim: ChatGPT producer on behalf of Njål; independent verification required.
- Owned files:
  - `.workclaims/2026-08-16-governed-incident-state.md`
  - `src/valo_kernel/contracts/incident.py`
  - `src/valo_kernel/contracts/__init__.py`
  - `tests/test_incident_contract.py`
- Dependencies: none; BARO/Veritas references remain opaque strings/digests.
- Boundary: Kernel owns deterministic operational incident state only. It does not diagnose, authorize remediation or execute effects.
