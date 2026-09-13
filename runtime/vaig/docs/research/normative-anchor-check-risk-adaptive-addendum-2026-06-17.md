# Normative Anchor Check — Risk-Adaptive Addendum

Date: 2026-06-17
Status: research addendum
Parent note: `docs/research/multilingual-governability-summary-2026-06-17.md`

## Core point

Normative Anchor Check should not run at full depth on every sentence.

That would create unnecessary latency, cost and operational drag.

The anchor should attach to consequential transitions.

The principle is:

```text
Do not anchor every sentence. Anchor every consequential transition.
```

Sharper:

```text
Fluency can be fast. State change must be governed.
```

## Why this matters

Fluent language can be handled quickly when the output is low-risk and non-state-changing.

The risk appears when the system changes rights, data, authority, access, money, records, obligations or accountability.

That is where normative drift becomes dangerous.

A model may sound locally correct while applying the wrong normative center.

Therefore the relevant trigger is not text generation.

The relevant trigger is transition.

## Three execution paths

### Fast path

Use for:

- low-risk output
- read-only explanation
- formatting
- summarization
- non-consequential language generation
- no state change
- no refusal
- no escalation
- no external action

Checks:

- language detection
- token inflation
- drift monitor
- confidence / uncertainty signal
- lightweight receipt if needed

No full Normative Anchor Check is required.

### Slow path

Use for:

- medium-risk output
- rising uncertainty
- semantic drift
- jurisdictional ambiguity
- unclear source grounding
- weak local terminology
- possible translation residue
- local legal / technical nuance uncertainty

Checks:

- retrieve local source
- verify jurisdiction
- require grounding
- preserve uncertainty
- controlled translation if needed
- route to stronger model or human review if unresolved

### Hard path

Use for consequential transitions.

Triggers:

- refusal
- fallback
- escalation
- approve / deny
- write / update / delete
- send / publish
- payment
- booking
- access change
- permission change
- data record change
- boundary change
- policy recalibration
- handoff to human authority
- any legal, health, financial, employment, public-sector or safety consequence

Checks:

- Normative Anchor Check must pass
- jurisdiction must be declared
- operating language must be declared
- domain must be declared
- local authority model must be visible
- valid normative source must be named
- allowed decision type must be verified
- receipt must preserve the transition

If the anchor cannot be established, the correct result is not fluent continuation.

The correct result is slow path, local source grounding, controlled translation, human review or halt.

## Decision table

```text
No state change + low risk
-> Fast path

No state change + rising drift / uncertainty
-> Slow path

State change or authority change
-> Hard path

Refusal / fallback / escalation
-> Hard path

Boundary or policy change
-> Hard path + boundary transition audit
```

## Relation to VAIG

VAIG should not waste full governance checks on every token stream.

VAIG should focus enforcement where the system crosses a boundary.

The key objects are:

- represented intent
- proposed transition
- authority state
- normative anchor
- consequence class
- audit receipt

This keeps latency acceptable while preserving governability.

## Relation to MECHA

MECHA remains the human decision-legitimacy layer.

Normative Anchor Check does not decide whether a human has legitimate authority.

It checks whether the system is operating from the correct local normative frame before a consequential transition reaches the human or execution layer.

## Runtime pattern

```text
model proposal
-> classify transition
-> fast / slow / hard path
-> apply anchor only where required
-> emit receipt
-> allow, re-scope, escalate, require human review or halt
```

## Minimal implementation signal

Each proposed action should expose:

```json
{
  "transition_type": "none | read | write | delete | send | approve | deny | refuse | fallback | escalate | boundary_change",
  "state_changing": true,
  "consequence_class": "low | medium | high | critical",
  "operating_language": "Norwegian",
  "jurisdiction": "Norway",
  "domain": "healthcare | finance | employment | public_sector | general",
  "normative_source": "named source or none",
  "anchor_required": true,
  "anchor_status": "pass | missing | weak | conflict",
  "decision": "allow | slow_path | require_local_review | halt"
}
```

## Research question

Can a risk-adaptive Normative Anchor Check reduce hybrid-center governance failures without making real-time agent systems unusably slow?

## Working conclusion

The answer is not to govern every sentence.

The answer is to govern every consequential transition.

That is where latency and legitimacy can be balanced.
