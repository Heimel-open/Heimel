# Relational Intelligence Observatory — RUN-001 MELLOMROM preflight

Date: 2026-08-23  
Status: `INSTRUMENT_READY_RAW_EPISODES_REQUIRED`

## Active question

Does a long human–AI research trajectory preserve task-relevant function that depends on the specific interaction lineage rather than on the same endpoint and the same amount of transcript information?

## Existing natural corpus anchor

The repository already contains MELLOMROM v0.1 with the intended natural unit:

```text
context_before
→ assistant_output
→ human_correction
→ assistant_repair
→ later_validation
```

It also prioritizes 15 chats from a 164-chat source set, led by chat 035, then 128/131 and the later continuity-heavy chats 151/162/163/164.

The checked-in MELLOMROM schema explicitly states that it is derived from two analysis documents and that raw episode extraction from the 164 chats has not yet been completed.

Therefore RUN-001 must not manufacture an empirical result from the candidate index.

## Instrument added

`experiments/relational_intelligence/mellomrom_lineage.py` now builds three matched conditions from frozen raw episodes:

```text
INTACT
SHUFFLED
ENDPOINT_MATCHED
```

The controls preserve:

- the exact episode multiset;
- the same starting episode;
- the same terminal episode;
- the same content volume;
- all original episode content.

They change only the interior lineage/adjacency.

This directly enforces the critical observatory control:

> More tokens are not the independent variable.

## Downstream scoring gate

Blinded downstream tasks are scored on `[0,1]` and must use the same task IDs across all three conditions.

The first bounded candidate gate is:

```text
mean(INTACT) >= 0.70
mean(INTACT) - mean(SHUFFLED) >= 0.10
mean(INTACT) - mean(ENDPOINT_MATCHED) >= 0.10
```

These are run defaults, not universal scientific thresholds.

A positive result would support only:

> the measured downstream function depends on the preserved tested lineage under information-volume-matched controls.

It would not by itself prove intelligence, symbiosis, consciousness, identity or a general theory of relational intelligence.

## Current evidence state

Synthetic observatory calibration is already positive by construction and validates detector plumbing only.

Natural RUN-001 is not yet scored because the raw MELLOMROM correction episodes are not present in the repository. This is a concrete data dependency, not a reason to redesign the experiment.

The next direct action is fixed:

```text
extract prioritized raw MELLOMROM episodes
→ freeze chronology
→ build matched control pack
→ run blinded downstream tasks
→ score intact vs shuffled vs endpoint-matched
```

No new theory phase is required before that run.

## CI policy

Validation for this research branch is local only. GitHub Actions status is ignored and is not used as evidence or as a gate.

Local branch-logic verification passed:

```text
LOCAL_CI_PASS
node_a=0.50
node_b=0.50
snapshot=0.50
full_relational_history=1.00
shuffled_history=0.125
rewired_relation=0.25

lineage scoring calibration:
intact=0.90
shuffled=0.50
endpoint_matched=0.5333333333
```

These values validate the synthetic/control paths only. They are not empirical MELLOMROM evidence.
