# unknown semantics — conservative fallback specification

status: draft for pr #12
date: 2026-06-14
rule: unknown != safe

## 1. the problem

vaig currently uses "unknown" as a dictionary fallback:

```python
label = level_names.get(level, "unknown")
action = level_actions.get(level, "unknown")
```

this means when a level is not in {0,1,2,3,4}, the system returns:
- label = "unknown"
- action = "unknown"

there is no defined behavior for what "unknown" means. the system continues operating with an undefined state. this is a safety gap.

## 2. the rule: unknown != safe

**unknown is not safe. unknown is not trusted. unknown is the absence of a verified decision.**

when the system cannot determine a known distrust level, it must fall back to the most restrictive safe behavior: **halt**.

## 3. when unknown occurs

| scenario | example | frequency |
|----------|---------|-----------|
| level outside 0-4 | corrupted level value, serialization error | rare |
| missing label lookup | new code adds level 5, old code doesn't know it | during upgrades |
| worm log read of legacy entry | pre-consolidation log with different label scheme | migration |
| ensemble returns invalid | instrument error produces non-standard level | bug |

## 4. conservative fallback semantics

```
if level not in {0, 1, 2, 3, 4}:
    label = "unknown"
    action = "halt"        # conservative: stop, don't proceed
    effective_level = 4    # treat as l4 for all safety checks
```

this is the **conservative** fallback. the alternative (permissive) would be:
```
    action = "pass"        # dangerous: proceed with unknown state
```
we do not implement the permissive path.

## 5. operator guidance

when unknown appears:
1. system halts (no output produced)
2. operator investigates cause
3. operator resets with admin_token after confirming safety
4. unknown count is logged as a system health metric

unknown should never appear in normal operation. if it does, it's a bug or a data corruption event.

## 6. scope for pr #12

- define the semantics (this document)
- implement `unknown_fallback` module with conservative behavior
- add tests verifying unknown -> halt
- **do not wire into ensemble.py** (uses legacy distrust engine)
- **do not wire into unified_distrust.py** (would change production behavior)
- keep as draft — wiring requires pr review

## 7. deferred wiring

| item | deferred to | reason |
|------|-------------|--------|
| wire into unified_distrust.py | consolidation pr | changes production behavior |
| wire into ensemble.py | consolidation pr | ensemble uses legacy engine |
| add unknown to worm schema | ssip schema pr | schema change |
| operator alert on unknown | query layer pr | needs metrics pipeline |
