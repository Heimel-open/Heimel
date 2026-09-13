# Work anchor — semantic identity integrity

- Repo: `nsolland/valo-kernel`
- Canonical base SHA: `91115f9460ea960413868ad6b07431a915f9d7ae`
- Branch: `feat/semantic-identity-integrity`
- Owner: ChatGPT for Njål / VALO Research
- Owned files: `src/valo_kernel/world/invariants.py`, `tests/test_semantic_identity.py`, `docs/semantic-identity-integrity.md`, this anchor
- Dependency: existing `WorldState`, `Fact`, `TruthStatus`, provenance/evidence model

Goal: make it impossible for pattern/similarity equivalence to silently become entity identity equivalence. Identity-equivalence claims must be explicit, evidence-backed, and refer to known entities. Pattern similarity remains evidence only.
