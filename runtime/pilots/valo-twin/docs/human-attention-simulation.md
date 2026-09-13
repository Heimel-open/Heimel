# Human Attention Simulation

Status: executable synthetic research harness  
Issue: #28  
Epistemic status: `implementation_claim` + `falsification_criterion`

## Research question

Can a digital-twin / continuity / authority stack reduce human attention load by routing only the work that genuinely needs human judgement, while preserving the ability to detect missed or misrouted attention?

This is the operational form of:

```text
Right human. Right attention. Right time.
```

The simulator does **not** establish that VALO can already predict real human-attention need. It measures the value and failure modes of the routing architecture under explicit synthetic assumptions.

## Modes

### STATIC_HITL

Every work item first receives human triage. Items that actually require specialist or principal judgement then receive a second human touch.

This is a conservative human-in-the-loop baseline.

### ATTENTION_ROUTED

A work item is allowed to remain autonomous only when all of these are true:

- predicted class is `AUTONOMOUS`;
- confidence is at or above the configured threshold;
- novelty is false;
- continuity uncertainty is false;
- authority uncertainty is false.

Anything else is routed directly to a human role.

The simulator records:

- human touches;
- human minutes;
- unnecessary human touches;
- missed required attention;
- wrong-role routes;
- principal interruptions;
- autonomous completions.

## Frozen reference workload

The reference scenario contains 10,000 synthetic work items:

| Class | Count | Human decision time | Route |
|---|---:|---:|---|
| known/delegated autonomous | 9,000 | 3 min baseline triage only | autonomous |
| domain judgement required | 700 | 8 min | domain expert |
| principal judgement required | 200 | 15 min | principal |
| uncertain / continuity-sensitive | 100 | 10 min | reviewer |

Every item costs 3 minutes of human triage in the static baseline.

The 100 uncertain items are intentionally labelled `AUTONOMOUS` by the classifier, but low confidence + novelty + continuity uncertainty force them to a human. This tests fail-closed attention routing rather than classifier optimism.

## Reference result

For the frozen synthetic workload:

```text
STATIC_HITL
human touches: 11,000
human minutes: 39,600
unnecessary human touches: 9,000

ATTENTION_ROUTED
human touches: 1,000
human minutes: 9,600
autonomous completions: 9,000
missed required attention: 0
wrong-role routes: 0
principal interruptions: 200
```

Derived synthetic effect:

```text
human minutes saved: 30,000 = 500 hours
human-minute reduction: ~75.8%
human-touch reduction: ~90.9%
attention amplification: 4.125x
human-touch reduction factor: 11x
```

These numbers are **not product performance claims**. They are the result of a deliberately frozen synthetic workload and must be replaced by historical replay and then true prospective data.

## Why this is falsifiable

The harness includes explicit failure cases.

If a work item truly requires human judgement but is predicted autonomous with high confidence and none of the novelty / continuity / authority guards fire, the simulator records `missedRequiredAttention`.

If a principal-required item is routed to a domain expert, the simulator records `wrongRoleRoutes`.

The architecture therefore does not define success as "fewer humans". Success requires fewer unnecessary touches **without unacceptable missed or misrouted judgement**.

## Historical replay next

The Njål-as-VALO historical replay lane should estimate these signals from time-locked evidence:

```text
P(human required | state, novelty, continuity, consequence, authority)
P(principal required | state, novelty, continuity, consequence, authority)
```

For each historical cutoff:

1. build the twin using only evidence available at or before the cutoff;
2. predict whether later recorded decisions required no human, a domain human, or the principal;
3. predict the role before revealing the actual later decision path;
4. compare predicted vs recorded attention;
5. measure unnecessary touches, missed attention, wrong-role routing and timing.

Historical replay remains retrospective and may contain leakage. True validation requires the sealed prospective T0 experiment.

## Core hypothesis

```text
AI scales work.
VALO may scale judgement by routing scarce human attention to the points where it is irreducible.
```

The hypothesis is weakened if attention routing cannot materially reduce unnecessary human load without increasing missed required judgement or wrong-role routing beyond an acceptable preregistered threshold.
