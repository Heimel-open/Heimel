# Claim — Policy Safety Instrument

- Owner: ChatGPT / Codex
- Repository: `nsolland/VAIG`
- Canonical base SHA: `daa097de6d0140506e381c31594a5e3693590dad`
- Branch: `feat/adopt-policy-safety-instrument`
- Delivery: adopt the Shieldstral signal as a provider-neutral policy-adaptive safety measurement slot inside VAIG
- Owned files:
  - `.claims/policy-safety-instrument.md`
  - `vaig/instruments/policy_safety_classifier.py`
  - `vaig/instruments/registry.py`
  - `vaig/instruments/__init__.py`
  - `tests/test_policy_safety_classifier.py`
  - `docs/shieldstral-adoption.md`
- Dependencies: existing `InstrumentBase`, registry and Ensemble native-input contract
- Verification: independent GitHub CI after PR creation
- Non-goals: model hosting, policy authoring, positive clearance, execution authority or enforcement
