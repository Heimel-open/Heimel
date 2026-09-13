# Security

`valo-distribution` is a **packaging and pinning** repo. It holds no runtime
secrets and no product logic. Security here is about supply-chain integrity.

## Secrets handling

- **Never commit secret values.** Only secrets *contracts* (name, required,
  source, format) live in `profiles/*.yaml` and config schemas.
- Real secret values are injected at deploy time by the target's secret manager
  (env, vault, sealed-secret, external KMS). Distribution references them by key.
- Rotation is the component repo's and operator's responsibility; distribution
  records the contract version, not the value.

## Pinning & provenance

- Every component is referenced by **tag + commit SHA + image digest**
  (`components/components.lock.yaml`).
- `scripts/build-bundle` records an SBOM and a provenance statement per bundle.
- Bundles are **signed** (see `RELEASE_PROCESS.md`). Public-key material for
  verification lives under `validation/` (public keys only).
- `scripts/verify-bundle` MUST be run before any deploy; a bundle without a valid
  signature or with an unpinned/unknown component is rejected.

## Signing keys

- Private signing keys are **never** in this repo.
- Public verification keys are committed; rotation is recorded in
  `validation/KEYS.md` (not the key file itself being secret — the public key is
  public).
- Compromise response: rotate key, re-sign all active bundles, record in receipt.

## Validation gates

- `validation/release-gates.yaml` defines required checks.
- A release that fails any gate is not signed and not deployed.
- `scripts/validate-distribution` is the executable gate runner.

## Rollback

- Every deploy produces a receipt. Rollback restores the prior receipt's pinned
  set. Rollback is itself receipted.
