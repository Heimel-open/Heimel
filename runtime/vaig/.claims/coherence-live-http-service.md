# Claim — Coherence live HTTP service

Owner: ChatGPT
Status: active
Canonical base: `2cf642eb4811eb4b6cf5809638d4add50eea3699`
Branch: `feat/coherence-live-http-service`

Owned files:
- `.claims/coherence-live-http-service.md`
- `vaig/coherence_service.py`
- `vaig/coherence_api.py`
- `tests/test_coherence_http_service.py`

Contract:
- Accept canonical CoherenceEvaluationInputV1 JSON.
- Evaluate inside VAIG using CoherenceEvaluationGateV1.
- Return the exact digest-bound CoherenceHandoffBindingV1 consumed by VALO Platform.
- Never create REHT clearance or execution authority.
