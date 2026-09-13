# Experimental Modules — outside VAIG Core scope

`SYSTEM_MAP.md` defines VAIG Core scope strictly: EvidenceCondition,
intent admissibility, authorization, execution/refusal, RRP handoff,
receipt. The modules below are exploratory work that lives in this
repository but is NOT part of that core, is not covered by
`TEST_EVIDENCE.md` claims, and must not be presented externally as VAIG
capabilities.

| Module | Status | Notes |
|--------|--------|-------|
| `src/reward_economy.py` | Experimental | VALO Credits token/incentive model. Speculative economics; no external claim support. |
| `src/value_weighting.py` | Experimental | Value weighting heuristics feeding the reward model. |
| `src/efficiency_engine.py` | Experimental | Efficiency metrics for the reward model. |
| `src/roi_gate.py` | Experimental | ROI-based gating exploration; not part of the AARM decision path. |
| `src/spend_gate.py` | Experimental | Spend control exploration; not part of the AARM decision path. |
| `src/model_router.py` | Experimental | Model selection routing exploration. |
| `baluko/` | Research | Authority governance research; background material, not runtime authority. |

## Rules

1. `TEST_EVIDENCE.md` remains the claim-to-evidence map for anything
   said externally about VAIG. Nothing in this list may be claimed.
2. Core code (under `src/vaig/`, `vacs/`, `reference_implementation/`)
   must not import from these modules.
3. Graduating a module out of this list requires tests, a
   `TEST_EVIDENCE.md` entry, and a `SYSTEM_MAP.md` update in the same PR.
