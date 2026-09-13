# Release Process

Canonical chain:

```
component release (canonical repo)
  → pinned distribution manifest (components/components.lock.yaml)
  → build (scripts/build-bundle)
  → validation (validation/release-gates.yaml)
  → signed bundle
  → deployment receipt (receipts/, verified by scripts/verify-bundle)
```

## 1. Component release (upstream)

A component (REHT, VAIG, Veritas, gateway, …) cuts a tagged release in its
canonical repo. Distribution does **not** participate in this step.

## 2. Pin (here)

Add/upgrade the component in `components/components.lock.yaml`:

```yaml
- name: reht
  repo: nsolland/reht
  tag: v1.4.2
  sha: 9f2c…          # exact commit SHA
  image: ghcr.io/nsolland/reht:v1.4.2
  digest: sha256:ab12…  # image digest, required
```

Pinning requires **tag + SHA + digest**. A missing digest blocks the build.

## 3. Build bundle

```bash
scripts/build-bundle --profile research
```

Produces a profile-scoped bundle (Compose/Helm/systemd artifacts + SBOM +
provenance). No component source is fetched or modified; only pinned artifacts
are assembled.

## 4. Validate

```bash
scripts/validate-distribution --bundle <bundle> --profile research
```

Runs `validation/release-gates.yaml`. Must pass all gates. A failing gate stops
the release.

## 5. Sign

The bundle is signed with the distribution private key (never committed). Public
key committed under `validation/`.

## 6. Deploy + receipt

Deploy consumes the signed bundle. `scripts/verify-bundle` runs first (signature
+ pins). On success a deployment receipt is written to `receipts/` and committed.

## 7. Rollback

```bash
scripts/verify-bundle --receipt receipts/<prior>.json
# restore prior pinned set from that receipt
```

Rollback is receipted like a forward deploy.

## Receipts

`receipts/` is the source of truth for "what is deployed". Each receipt names
every pinned component (tag/sha/digest), the profile, the bundle hash, the signer
and the timestamp. Receipts are append-only and committed.
