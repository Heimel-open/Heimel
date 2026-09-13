# Distribution Contract

This document is the boundary contract for `valo-distribution`. It is the
authoritative statement of what this repo may and may not contain.

## Scope (IN)

`valo-distribution` owns:

1. **Installation & upgrade** — deterministic install/upgrade of pinned component
   sets onto a target appliance.
2. **Appliance profiles** — `edge`, `research`, `enterprise`, `demo`
   (`profiles/*.yaml`). Each profile selects a subset of pinned components plus
   profile-specific config/resource bounds.
3. **Packaging** — Compose (`compose/`), Helm (`helm/`), systemd (`systemd/`).
4. **Pinning** — release SHAs and image digests in `components/components.lock.yaml`.
5. **Configuration & secrets contracts** — declarative config schemas and
   secrets *contracts* (what a secret is named, required, sourced — never the
   secret value). Adapter selection (which provider/adapter a profile uses).
6. **SBOM, signing, provenance** — generation, collection, signing of bundles.
7. **Release validation & receipts** — gates (`validation/release-gates.yaml`),
   validation script, signed deployment receipts (`receipts/`).
8. **Rollback & migration** — recorded, reversible procedures keyed to receipts.

## Scope (OUT — hard boundary)

`valo-distribution` MUST NOT contain product logic:

- No REHT, VAIG, Veritas, RACS, Core, gateway, Speider, BARO source or behavior.
- No component implementation, fixes, or features.
- No forks of canonical component repos.

It references components **only by tag + pinned SHA / image digest**. If a
behavior change is needed in a component, that change happens in the component's
canonical repo; distribution re-pins after the component releases.

## Canonical chain

```
component release (canonical repo)
  → pinned distribution manifest (components/components.lock.yaml)
  → build (scripts/build-bundle)
  → validation (validation/release-gates.yaml)
  → signed bundle
  → deployment receipt (receipts/, verified by scripts/verify-bundle)
```

Each link is recorded; the deployment receipt is the only artifact a runtime
operator needs to prove what is deployed and from which exact pins.

## Authority

- Distribution may pin, package, validate, sign, deploy, roll back.
- Distribution may NOT alter component behavior or bypass component release gates.
- A component release that fails its own canonical gates is never pinned here.
