# Claim: AI Transition & Resistance Evaluator runtime

- Date: 2026-08-11
- Owner: ChatGPT for Njål Solland
- Repository: `nsolland/VAIG`
- Canonical base SHA: `0b96b91e1e97a37c082b50cd16a24a2f2eada944`
- Branch: `feat/ai-transition-resistance-evaluator`
- Delivery: implement bounded runtime evaluation for Human/Institutional AI Transition Risk (HITR) and Political Realignment Risk (PRR) from normalized, provenance-bearing evidence.
- Owned files:
  - `.claims/ai-transition-resistance-evaluator.md`
  - `vaig/transition_risk.py`
  - `tests/test_transition_risk.py`
  - `vaig/__init__.py` (exports only)
- Dependencies: Python stdlib only; existing VAIG evidence/evaluation boundaries.
- Exclusions: no partisan prediction; no inference that exposure equals job loss; no execution authority; no reht/RACS/Gateway semantics change.
- Required behavior: preserve component dimensions; reject missing/stale/invalid critical evidence; return explicit UNKNOWN/INSUFFICIENT_EVIDENCE states; composite scoring only when evidence is decision-grade enough for the configured policy.
