# Distribution Contract — Skills Registry

This document is the boundary contract for `valo-skills-registry`. It mirrors the
hard boundary in `valo-distribution`'s DISTRIBUTION_CONTRACT: this repo is a
deterministic catalog/contract layer.

## IN — this repo owns
1. Canonical skill manifests (`skills/<domain>/<id>.yaml`).
2. Schema enforcement (`schemas/skill.schema.json`).
3. Versioning + dependency resolution metadata.
4. Risk class, I/O contracts, provider metadata, delegation/retention rules.
5. Signed manifests (`trust/` + signature fields in manifest `integrity`).
6. Validation CLI (`cli/validate.py`) and signing helper.

## OUT — this repo MUST NOT
- Evaluate evidence, authorize actions, or execute skills. (REHT/RACS/Gateway own that.)
- Move or reimplement runtime code from `valo-platform` / `valo-runtime-*`.
- Alter REHT/RACS boundaries.
- Store secrets or live capability state.

## Link to capability_registry
A skill manifest references required capabilities by id. The binding between a skill
and an *allowed* capability lives in `valo-platform/capability_registry` — not here.
This repo only declares `spec.capabilities.requires`; `valo-platform` governs whether
the agent currently holds that capability as mandate.

## Signing
- Manifests carry `integrity.package_digest` (sha256) and `integrity.signature`.
- Private keys never in this repo; public keys under `trust/`.
- `cli/validate.py` verifies schema + digest; `cli/sign.py` (operator-side) produces
  the signature outside this repo's committed state.
