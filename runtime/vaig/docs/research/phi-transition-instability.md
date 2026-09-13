# Phi Transition Instability

Status: research note
Scope: VAIG / Phi / Semantic Circuit Breaker / Normative Drift

## Core point

Phi should not read one isolated signal.

It should read breaks in the golden thread.

The question is not:

```text
Did the wording change?
```

The question is:

```text
Did the transition change the operational relation between premise, evidence, authority, obligation, action and consequence?
```

## Definition

Phi detects instability when a transition preserves linguistic coherence but changes the operational relation between evidence, authority, obligation and consequence.

In plain language:

```text
Phi triggers when the language still hangs together, but the governance relation has changed.
```

## Natural nuance vs governance break

A natural linguistic nuance is acceptable when it preserves:

- same actor
- same obligation
- same authority
- same evidence basis
- same jurisdiction
- same consequence
- same stop-right
- same accountability

A governance break occurs when one or more of these changes without explicit grounding or authorization.

## Example: safe nuance

Original:

```text
Human approval is required.
```

Transformation:

```text
A designated reviewer must approve before execution.
```

Assessment:

The wording changed, but the golden thread is preserved.

- obligation remains binding
- approval remains required
- human authority remains present
- execution remains blocked until approval

This should not trigger hard path.

## Example: normative drift

Original:

```text
Human approval is required.
```

Transformation:

```text
A reviewer is notified before execution.
```

Assessment:

Approval became notification.

The human moved from authority to awareness.

This is not a language nuance.

It is authority loss.

This should trigger VAIG.

## Phi signal vector

Phi should be modeled as a vector, not a single scalar.

Suggested dimensions:

```text
premise_delta
evidence_delta
authority_delta
modality_delta
jurisdiction_delta
consequence_delta
reversibility_delta
accountability_delta
```

Each dimension measures whether the transition preserved, weakened, transformed or broke the relevant governance relation.

## Risk interpretation

### Low risk

Only linguistic form changed.

The golden thread remains intact.

Examples:

- wording refinement
- local idiom adjustment
- harmless paraphrase
- same actor, same obligation, same consequence

Action:

```text
allow / monitor
```

### Medium risk

Meaning, premise or evidence changed.

Examples:

- new assumption introduced
- evidence basis weakened
- original uncertainty removed
- jurisdiction becomes unclear

Action:

```text
watch / slow_path / require_source_grounding
```

### High risk

Authority, obligation, prohibition, stop-right or consequence changed.

Examples:

- must -> should -> may
- approve -> review -> receive notice
- cannot proceed -> proceeds unless stopped
- named accountable role -> generic process

Action:

```text
require_human_review / Normative Anchor Check
```

### Hard stop

Action can occur with lower authority than originally required, or without proper evidence / jurisdictional anchor.

Examples:

- execution proceeds without required approval
- automated action replaces human authority
- irreversible state change occurs without valid authorization
- governance language survives but authority disappears

Action:

```text
halt
```

## False positive control

Phi should not trigger hard path on one word in isolation.

A single modal shift may be a warning, not a failure.

The stronger signal is a pattern across the transition.

Example weak signal:

```text
must -> should
```

Example strong signal:

```text
must -> should
approve -> review
cannot proceed -> proceeds unless stopped
```

The second pattern indicates real drift.

Phi should therefore evaluate transition patterns, not isolated vocabulary.

## Relation to sensor layer and VAIG

The practical architecture is:

```text
A detects drift.
C governs drift.
B would prevent drift, but requires a different model architecture.
```

Where:

- A = sensor layer / semantic circuit breaker
- C = VAIG governance event handling
- B = future model-native stability validation

Current implementation should focus on C with A as sensor input.

The sensor detects possible transition instability.

VAIG decides whether the instability requires watch, slow path, source grounding, human review or halt.

## Operational rule

Do not stop the model because a sentence changes.

Stop or slow down when the change alters:

- premise
- evidence
- authority
- obligation
- jurisdiction
- consequence
- reversibility
- accountability

## Core formulation

```text
Semantic variation is not the problem.
Transition instability is the problem.
```

```text
Phi measures whether the golden thread survives the transition.
```

```text
If the language remains coherent but authority, evidence or consequence moves, Phi should trigger VAIG.
```
