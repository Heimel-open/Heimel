# ensemble.py drift — documented, not fixed

date: 2026-06-14
status: acknowledged, scheduled for future consolidation pr

## finding

`vaig/ensemble.py` imports from legacy modules:

- line 19: `from vaig.core.distrust import DistrustEngine`  — should be `vaig.core.unified_distrust.UnifiedDistrustEngine`
- line 20: `from vaig.core.worm_log import WORMLog`  — should be `vaig.core.unified_worm.UnifiedWORMLog`
- line 83: instantiates `DistrustEngine` (legacy, no per-source tracking)
- line 84: instantiates `WORMLog` (legacy, no schema versioning)

## impact

unified distrust engine (per-source tracking, trend slope, l4_auto_trigger) and unified worm log (schema versioning, hash chain) exist but are **not used in production path**. ensemble.py uses the pre-consolidation implementations.

## why not fixed now

per runner protocol: document, do not refactor. this is a consolidation pr, not a why gate pr. switching imports changes production behavior and requires full regression testing. out of scope for pr #8 and pr #12.

## future fix

pr: consolidation — switch ensemble.py to unified imports
- switch `DistrustEngine` → `UnifiedDistrustEngine`
- switch `WORMLog` → `UnifiedWORMLog`
- full regression test (54 tests + ensemble integration tests)
- blocked until: query layer pr (worm read api) is merged
