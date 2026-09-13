# VAIG Coherence services

This deployment pack runs the canonical evaluator and the canonical second-operator replay as separate service processes. It does not copy or reimplement their evaluation semantics.

## Services

Evaluator:
- image: `deploy/coherence/Dockerfile.evaluator`
- port: `8002`
- health: `GET /healthz`
- evaluation: `POST /api/v1/coherence/evaluate`
- required secret: `VAIG_COHERENCE_TOKEN`

Second-operator replay:
- image: `deploy/coherence/Dockerfile.replay`
- port: `8003`
- health: `GET /healthz`
- replay: `POST /api/v1/coherence/replay`
- required identity: `VAIG_COHERENCE_REPLAY_OPERATOR_REF`
- required secret: `VAIG_COHERENCE_REPLAY_TOKEN`

The two services must use distinct service identities/credentials in production. The replay operator identity must also differ from the evidence producer identity carried by the replay request.

## Local/container run

From the repository root:

```bash
export VAIG_COHERENCE_TOKEN='replace-me'
export VAIG_COHERENCE_REPLAY_OPERATOR_REF='operator:vaig-replay-2'
export VAIG_COHERENCE_REPLAY_TOKEN='replace-me-too'
docker compose -f deploy/coherence/docker-compose.yml up --build
```

The platform can then use:

```text
VAIG_COHERENCE_URL=http://127.0.0.1:8002
VAIG_COHERENCE_REPLAY_URL=http://127.0.0.1:8003
```

with matching bearer tokens. Production remote URLs must be HTTPS.

## Deployment boundary

These services produce evaluation/replay evidence only. Neither service can create execution authority or REHT clearance. A VAIG PASS is therefore not permission to execute; downstream REHT remains required.

The bootstrap files intentionally avoid importing the broad `vaig/__init__.py` surface. They expose the repository's `vaig` directory as a package path and import only the canonical Coherence service modules.

## Current external blocker — 2026-08-24

A direct deployment attempt to the connected Vercel team `valorg` was rejected with HTTP 402 / `resource_creation_blocked`: the Pro subscription is suspended and Vercel requires a valid payment method before creating a deployment. No external deployment success is claimed until that account-level blocker is removed or another deployment provider is connected.
