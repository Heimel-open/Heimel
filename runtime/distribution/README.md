# valo-distribution

Distribution repository for the VALO ecosystem. **This repo contains no product
logic.** It is the single place for:

- installation and upgrade of VALO components
- appliance profiles: `edge`, `research`, `enterprise`, `demo`
- packaging: Compose / Helm / systemd
- pinned release SHAs and image digests
- configuration, secrets contracts and adapter selection
- SBOM, signing and provenance
- release validation and receipts
- rollback and migration
- bounded commercial pilot packaging that references canonical runtime owners

## Current deployability state

**NOT DEPLOYABLE from `components/components.lock.yaml` yet.**

The current lock still contains bootstrap placeholders (`v0.0.0`, zero SHAs and
zero image digests) and historical repository references. Release gates MUST fail
closed on those values. A syntactically valid placeholder is not an artifact.

`components/source-candidates-2026-08-20.yaml` records exact canonical source
commits observed while preparing the first Execution Assurance bundle. It is
explicitly **not** a distribution lock. Missing release tags, images and immutable
image digests remain `NOT_ESTABLISHED` until independently observed from the
canonical component release process.

Promotion rule:

```text
canonical source commit
→ released tag bound to that exact SHA
→ published immutable artifact/image digest
→ components.lock.yaml
→ distribution gates
→ bundle
```

No missing artifact identity may be synthesized to make the bundle green.

## Canonical chain

```
component release
  → pinned distribution manifest (components/components.lock.yaml)
  → build (scripts/build-bundle)
  → validation (validation/release-gates.yaml + scripts/validate-distribution)
  → signed bundle (scripts/build-bundle + signing)
  → deployment receipt (receipts/, verified by scripts/verify-bundle)
```

## Principle

`valo-distribution` **consumes only tagged and pinned artifacts**. REHT, VAIG,
Veritas, the gateway and all other components live in their canonical repos. This
repo pins them by SHA/digest and packages them — it does not fork or reimplement
them. This collects distribution responsibility without creating another
monolith.

## Product/pilot packages

`pilots/` may contain **packaging contracts for bounded commercial offers**. They
must not copy product/runtime logic or become new architecture owners.

Current package:

- [`pilots/execution-assurance-v1/`](pilots/execution-assurance-v1/) — **Execution Assurance Pilot v1**: one bounded consequence-bearing workflow, SHADOW by default, evidence/replay/agreement metrics, and optional progression toward enforcement only through the existing governed mode-promotion and REHT execution path.

A reusable pilot template may leave runtime pins empty. Before it can be called a
deployable bundle, every included canonical component must be pinned to an
immutable artifact/source SHA and pass the normal distribution release gates.

## Layout

| Path | Purpose |
|------|---------|
| `profiles/` | appliance profiles (edge/research/enterprise/demo) |
| `pilots/` | bounded commercial packaging contracts; no runtime logic |
| `components/components.lock.yaml` | deployable component lock; must contain real release/artifact pins |
| `components/source-candidates-*.yaml` | non-deployable source snapshots; never consumed by build-bundle |
| `schemas/` | JSON Schema for manifest, receipt and package contracts |
| `compose/`, `helm/`, `systemd/` | packaging per target |
| `scripts/` | validation/build/verification commands |
| `validation/release-gates.yaml` | release gate definitions |
| `receipts/` | signed deployment receipts (git-kept) |
| `tests/` | distribution-level tests |

## Workflow

See `RELEASE_PROCESS.md`, `DISTRIBUTION_CONTRACT.md`, `SECURITY.md`.
