# Relygon → relAIon migration

Status: CANONICAL MIGRATION RULE

`Relygon` is the former name of `relAIon`. It is not a separate product, architecture, identity, or future development track.

## Canonical ownership

The canonical home for relAIon is `nsolland/PersonalAI-OS`, under `docs/relaion/` plus the corresponding `src/paios/` domain implementation.

All material created under the Relygon name must be handled as relAIon lineage:

- active semantics are absorbed into relAIon;
- historical source is retained with provenance when useful;
- duplicate or superseded variants are not allowed to become competing canon;
- generic VALO infrastructure remains in its owning repository and is referenced as a dependency rather than copied into relAIon;
- no new work may use Relygon as the current product name.

Historical references may retain the literal name `Relygon` where changing it would falsify provenance. Such references mean `relAIon (formerly Relygon)`.

## Material already inside PersonalAI-OS

The following legacy documents are preserved under `docs/relaion/legacy/relygon/`:

- `relygon-capability-development.md`
- `relygon-device-compatibility.md`
- `relygon-embodiment.md`
- `relygon-opportunity-engine.md`

They are source lineage, not a second architecture tree. Canonical relAIon documents may absorb, narrow, split, or supersede their claims.

## Estate inventory outside PersonalAI-OS

The estate-wide Relygon search identified material in other repositories. These are part of relAIon lineage but remain in place when their implementation belongs to another architectural owner.

### valo-kernel

Legacy product and node material:

- `docs/products/relygon-product-model.md`
- `docs/products/relygon-copilot-pc-mvp.md`
- `docs/products/relygon-cross-platform-node.md`
- `docs/products/relygon-mobile-node-contract.md`
- `src/valo_kernel/relygon_pc_bootstrap.py`
- `tests/test_relygon_pc_bootstrap.py`
- `installer/linux/install-relygon-pilot.sh`
- `installer/macos/install-relygon-pilot.sh`
- `installer/windows/Install-RelygonPilot.ps1`
- `installer/windows/Install-RelygonPilot.cmd`
- `installer/windows/Build-RelygonPilotBundle.ps1`
- Relygon references in browser-extension, capability-scout, NVIDIA/local bootstrap, mobile capability adapter, capability inference fabric, and related installer/runtime material.

Migration rule: relAIon owns the product/identity/development semantics; kernel-owned execution, adapter, installer, gateway, and enforcement primitives remain kernel infrastructure. Any live relAIon use of them must depend on the generic capability contract rather than create a new Relygon authority layer.

### valo-platform

Legacy material includes:

- `.claims/relygon-capability-growth-v1.md`
- `docs/personal-ai-capability-growth.md`
- Relygon references in personal-AI care/becoming material.

Migration rule: developmental semantics belong in relAIon; generic governed infrastructure remains in valo-platform.

### valo-factory

Legacy domain classification contains Relygon references in `lib/need_domains.py` and tests. These are legacy aliases/classification inputs, not a separate product.

### Index and research/business estate

Relygon appears in historical business, capability-loop, master-index, and book/research material. Those references are provenance. Current references should use relAIon unless discussing the historical name explicitly.

## Canonical interpretation rules

When old Relygon material conflicts with current relAIon canon:

1. current explicit relAIon canon wins;
2. older Relygon material is evidence/history, not automatic authority;
3. useful missing capability is migrated through an explicit relAIon acceptance contract;
4. no old Relygon implementation is promoted merely because it exists or once passed tests;
5. identity, seed, continuity, memory, relationships and development remain relAIon/PersonalAI-OS concerns;
6. consequence authority remains outside the worker/identity layer and crosses the governed VALO consequence path where effects are consequential.

## Naming invariant

Current name: **relAIon**.

Legacy alias: **Relygon**.

No new current-facing file, API, product surface, architecture claim, package, or runtime should introduce `Relygon` except for explicit compatibility/provenance handling.
