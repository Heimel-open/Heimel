# Claim — Coherence service deployment

Owner: ChatGPT
Status: complete packaging / external deployment blocked
Canonical base: `a9159357ef5bd710f6d2b1bb6bbbbd96a385c7e4`
Branch: `deploy/coherence-services`

Primary objective:
- Make the canonical VAIG Coherence evaluator and second-operator replay independently deployable without copying or reimplementing evaluation semantics.

Invariants:
- Evaluator and replay run as separate service processes.
- Both load the canonical `vaig/coherence_*` modules directly from the repository.
- Deployment bootstrap must not execute the broad `vaig/__init__.py` import surface merely to start Coherence services.
- Replay requires a distinct operator identity and bearer token.
- Evaluator output remains evidence only and cannot issue execution authority.
- Replay output remains evidence only and cannot issue execution authority.
- REHT remains the downstream execution-authorization boundary.

Owned files:
- `.claims/coherence-service-deployment.md`
- `deploy/coherence/evaluator_app.py`
- `deploy/coherence/replay_app.py`
- `deploy/coherence/Dockerfile.evaluator`
- `deploy/coherence/Dockerfile.replay`
- `deploy/coherence/docker-compose.yml`
- `deploy/coherence/README.md`

Validation:
- The minimal synthetic-package bootstrap pattern was executed locally against a dummy `vaig.coherence_api` module and passed.
- Hosted GitHub Actions for the branch ended in the repository's existing `startup_failure` before jobs; no hosted test success is claimed.

External deployment attempt:
- Vercel team `valorg` rejected a new deployment with `resource_creation_blocked` / HTTP 402 because the Pro subscription is suspended and requires a valid payment method.
- No alternate connected deployment provider is available.
- No external service success is claimed while that account-level blocker remains.
