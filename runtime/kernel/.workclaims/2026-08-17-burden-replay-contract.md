# Work claim: Burden + Replay Contract

Owner: ChatGPT on behalf of Njål / VALO
Canonical base: c510ebdb5a3ed8ead375beaf884146301c4d33d6
Branch: feat/burden-replay-contract

Active delivery: adopt the general operational pattern of explicit burden accounting, evidence-complete replay, and change-triggered re-evaluation as provider- and domain-neutral Kernel contracts without moving authorization or execution into Kernel.

Owned files:
- src/valo_kernel/contracts/burden_replay.py
- tests/test_burden_replay.py
- docs/burden_replay_contract_v1.md
- src/valo_kernel/contracts/__init__.py
- .workclaims/2026-08-17-burden-replay-contract.md

Dependencies:
- existing canonical digest semantics
- existing Evidence references and governed WorldState admission remain authoritative
- fresh REHT authorization, deterministic RACS outcome, PEP enforcement and Veritas effect evidence remain external boundaries

Invariants:
- burden records describe consequence exposure; they do not create authority
- every burden binds a consequence, unit, responsible bearer, evidence references and enforcement/control reference
- missing required replay material fails replay completeness deterministically
- material state/change triggers invalidate prior replay completeness until affected scope is re-evaluated
- failed hard requirements cannot be offset by aggregate scoring
- replay is boundary/object replay, not token-by-token model replay
- no direct effect path is introduced

Source note:
- external convergence observed in Garlando McCord Sr., Data Center Placement Control Layer — Final Operational Completeness Addendum (2026): evidence minimums, burden ledger, replay, change triggers, hard gates and anti-drift. VALO adopts only the general operational pattern and preserves its independent execution-governance architecture and terminology.
