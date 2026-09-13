# One-shot Factory lane

Status: **F1 implemented; local release-candidate path complete**  
Upstream gate: F0 `PortfolioBuildProfileV1 → BuildOrderV1` compiler  
Catalog: `config/one_shot_profiles.json`  
Generator: `lib/one_shot_scaffold.py`  
CLI: `bin/valo-one-shot-scaffold`

## Purpose

Turn the portfolio backlog into throughput without turning every idea into a repository, runtime or permanent product line.

```text
Idebank mission / product idea
→ portfolio placement
→ PortfolioBuildProfileV1
→ F0 compiler
→ bounded BuildOrderV1
→ F1 one-shot profile
→ thin local application candidate
→ generated smoke PASS
→ exact target SHA release binding
→ normal separately governed release/deploy path
```

The generator does not push, merge, deploy, publish, spend or execute external actions.

## Eight reusable profiles

The current 77 one-shot records are represented by eight templates:

| Profile | Current mapped records | Default surface |
|---|---:|---|
| `accessibility-utility` | 13 | static PWA |
| `ageing-utility` | 10 | static PWA |
| `care-utility` | 2 | static PWA |
| `community-utility` | 11 | thin web app |
| `general-utility` | 13 | static PWA |
| `preservation-utility` | 7 | static PWA |
| `public-service-utility` | 10 | static PWA |
| `worker-utility` | 11 | static PWA |

These are **Factory templates, not eight new products**.

## Commodity slots

Every F1 build resolves the same nine F0 reuse categories:

- model/inference;
- rendering/media;
- auth/identity transport;
- scheduling/queues;
- storage/database;
- connectors/API clients;
- UI framework;
- deployment/runtime;
- observability.

Resolution order:

1. `NOT_NEEDED` → no component;
2. explicit `REUSE.provider_or_component` → use that replaceable component;
3. `REUSE` without a component → use the selected profile's replaceable catalog default;
4. `CUSTOM_REQUIRED` → only accepted when F0 contains an evidence reference.

The catalog uses capability slots such as `replaceable:static-host`, not strategic provider dependencies.

## Generated candidate

A successful scaffold contains:

- `index.html`
- `app.js`
- `app.css`
- `manifest.webmanifest`
- `app.config.json`
- `product.contract.json`
- `release-candidate.json`
- `smoke_test.py`
- `README.md`
- `scaffold-manifest.json`

A bound candidate additionally contains:

- `release-binding.json` — exact target SHA, portfolio SHA, profile digest, BuildOrder id and deterministic artifact digest;
- updated `release-candidate.json` with `state: CANDIDATE_BOUND`.

The initial UI is deliberately minimal. Product-specific behavior comes from the bounded build order and acceptance criteria; the scaffold is not another application framework.

## Governance invariant

Generated configuration contains:

```text
direct_effect_path = false
authority_effect = none
```

If an application later sends a message, spends money, publishes, changes enterprise state, controls a device, or otherwise creates consequences, that adapter must use the existing governed execution boundary.

F1 cannot introduce `NEW_PRIMITIVE_ESTABLISHED`. A one-shot build that supposedly requires a new core primitive returns upstream for architecture review.

## Local generation

Unbound candidate:

```bash
valo-one-shot-scaffold \
  profile.json \
  authority-context.json \
  --factory-profile community-utility \
  --app-slug volunteer-shift-swap \
  --output-dir ./candidate
```

Verified and exact-SHA bound release candidate:

```bash
valo-one-shot-scaffold \
  profile.json \
  authority-context.json \
  --factory-profile community-utility \
  --app-slug volunteer-shift-swap \
  --output-dir ./candidate \
  --verify \
  --target-source-sha <40-hex-target-sha> \
  --release-version 0.1.0
```

`--target-source-sha` and `--release-version` must be supplied together. Binding automatically runs the generated smoke test first; a failing smoke cannot produce release evidence.

The output directory must be absent or empty. The generator refuses to overwrite an existing candidate.

## Product smoke

Every candidate includes a dependency-free smoke test:

```bash
python3 candidate/smoke_test.py
```

Before binding it checks that the expected product/config/release files exist, no direct effect path is declared, authority effect remains `none`, and the release is still `CANDIDATE_UNBOUND`.

## Release binding

`bind_release(...)` and the CLI binding path bind a generated artifact set to:

- semantic release version;
- exact target repository SHA;
- exact portfolio source SHA;
- exact PortfolioBuildProfile digest;
- BuildOrder id;
- deterministic artifact digest.

This creates a `thin-app-release-binding.v1` record. Binding proves lineage; it does not authorize deployment.

## F1 exit criterion

The implementation-level F1 path now exists end-to-end:

```text
validated portfolio build profile
→ F0 compile
→ one target repo
→ one selected Factory profile
→ materialized thin-app candidate
→ generated smoke PASS
→ exact target SHA bound into release evidence
```

The remaining portfolio-level validation is to run this path against one current real Idebank mission and normal independent QC/release/deploy controls. After that, repeated ideas should be measured as Factory throughput. Promotion into a persistent P4 product requires separate product-boundary evidence.
