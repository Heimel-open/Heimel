# Work anchor — RuView physical evidence

Status: in progress
Date: 2026-08-09
Owner: ChatGPT execution worker
Claim: RuView physical-world evidence adapter and adoption boundary

## Base

- repository: `nsolland/valo-edge`
- canonical base SHA: `4ec4ba40fdc37da355954fdc32b061261690c9f2`
- branch: `feat/ruview-physical-evidence`
- draft PR: opened from this anchor before substantive implementation

## Owned files

- `docs/work-anchors/ruview-physical-evidence-2026-08-09.md`
- `docs/edge/ADR_RUVIEW_PHYSICAL_EVIDENCE.md`
- `src/valo_edge/adapters/ruview.py`
- `src/valo_edge/adapters/__init__.py`
- `tests/test_ruview_adapter.py`

## Dependencies and boundary

- Upstream: RuView structured WiFi CSI observations and version/provenance metadata.
- VALO Edge treats RuView output as evidence/proposal input only, never authority or physical truth.
- No direct RuView-to-actuator, RuView-to-authoritative-state, or model-to-storage path.
- Downstream authoritative world state remains owned by `nsolland/valo-kernel`; evidence must be verified/admitted and converted to a canonical Kernel event before it can affect `WorldState`.
- REHT/micro-REHT remains the execution authorization boundary.
- This work does not modify `valo-kernel` and does not collide with its open WorldPack PR #4.
