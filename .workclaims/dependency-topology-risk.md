# Work claim: Dependency Topology and Concentration Risk

Owner: ChatGPT on behalf of Njål / VALO
Canonical base: 0b50c18bbcc59bf36e26a8613e33142b34f30764
Branch: feat/dependency-topology-risk

Active delivery: encode dependency topology and concentration-risk semantics so apparent redundancy cannot hide shared authority, provider, jurisdiction, credential/control-plane, execution/PEP, or recovery dependencies.

Owned files:
- src/valo_kernel/contracts/dependency.py
- src/valo_kernel/contracts/__init__.py
- src/valo_kernel/dependency_risk.py
- tests/test_dependency_risk.py
- docs/dependency_topology_v1.md
- .workclaims/dependency-topology-risk.md

Dependencies:
- existing canonical_digest helper
- existing fail-closed Kernel contract conventions
- REHT remains the external authorization boundary; this feature creates no clearance

Invariants:
- redundancy is evaluated across dependency and authority domains, not topology alone
- shared dependency concentration is explicit and deterministic
- unknown or incomplete required dependency evidence cannot be treated as independence
- no single dependency may silently become transit power over governed execution
- this layer creates no authority, no execution permission and no direct effect path
