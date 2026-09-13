# Work anchor — enforceable WorldPack extensions

Status: in progress
Issue: #3
Date: 2026-08-09
Owner: ChatGPT execution worker
Review requirement: independent architecture review before merge

## Base

- repository: `nsolland/valo-kernel`
- canonical base SHA: `108f770998f15a0265f3c7bcc5264cc9bb13f208`
- branch: `feat/enforceable-world-packs`

## Owned files

- `docs/work-anchors/enforceable-world-packs-2026-08-09.md`
- `src/valo_kernel/contracts/common.py`
- `src/valo_kernel/contracts/entity.py`
- `src/valo_kernel/contracts/relationship.py`
- `src/valo_kernel/contracts/events.py`
- `src/valo_kernel/packs/base.py`
- `src/valo_kernel/kernel/engine.py`
- `src/valo_kernel/kernel/reducers.py`
- `tests/test_world_packs.py`

## Contract

Registered namespaced pack types are accepted. Unregistered types, core overrides and namespace collisions fail closed. Pack reducers remain subordinate to Kernel tenant, version, idempotency, chain and invariant checks.
