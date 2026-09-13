# Multilingual Governability — Working Summary

Date: 2026-06-17
Status: research note
Scope: VAIG / Governability / AI Economy Optimizer

## Core conclusion

Multilingual fluency is not multilingual governability.

A model does not truly support a language just because it can answer in that language.

For governance, the harder question is whether the model can preserve refusal, escalation, boundary decisions, legal nuance and auditability in that language.

If safety has only been validated in English, then universal safety has not been demonstrated.

Only English-language safety has been demonstrated.

## Main distinction

Language support is the wrong metric.

The relevant distinction is:

### Language capability

The model can read and write the language.

### Language safety

The model can follow policy in that language.

### Language governability

The model can refuse, escalate, explain, document and preserve accountability in that language.

A language is not truly supported unless refusal, escalation and auditability are supported in that language.

## Three-layer problem

There are three separate layers that can fail independently or reinforce each other.

### 1. Language layer

The language itself has its own semantic density, nuance, cultural context, legal vocabulary, idioms and technical precision.

This is the expressive capacity of the language.

### 2. Tokenizer layer

The infrastructure splits the language into billable and processable units.

A language may be semantically compact but still become expensive because the tokenizer is poorly adapted to it.

Token inflation is therefore an infrastructure artifact, not proof that the language is less efficient.

### 3. Model representation layer

The model may not represent the language with the same stability as its dominant training language.

Training data, alignment, safety tests and benchmarks are often centered on English.

That can create semantic drift, weaker refusal precision and less reliable audit traces in other languages.

## Cascading inequality

The problem is not one inequality.

It is a cascade:

```text
language capacity
-> tokenizer mismatch
-> representation instability
-> boundary decision instability
-> weak auditability
```

Small or non-dominant languages may therefore face double or triple cost:

- higher token cost
- weaker semantic stability
- less validated governance behavior

## Linguistic center of gravity

A model has no human language in the ordinary sense.

It has a representational space.

If training data, tokenizer, alignment and evaluation are dominated by one language, the model develops a linguistic center of gravity.

Other languages are then not simply alternative expressions.

They are projected into or around that learned center.

Hypothesis:

```text
Language distance from the model's learned center predicts governability failure.
```

More formal version:

```text
A model's linguistic center of gravity predicts semantic stability, hallucination rate and governance reliability across languages.
```

## What must be tested

The test must not only ask whether the model can answer.

It must ask whether governance behavior survives across languages.

For the same scenario across multiple languages, measure:

- input token cost
- output token cost
- semantic drift
- hallucination rate
- refusal consistency
- fallback consistency
- escalation consistency
- boundary decision consistency
- audit trace completeness
- legal / technical nuance preservation

## Paired-case method

Use the same governance case in multiple languages.

Each case should preserve the same intended meaning.

Compare:

```text
same scenario
same intended meaning
same expected boundary result
different language
```

Then evaluate:

- Did token cost change?
- Did meaning shift?
- Did the boundary decision change?
- Did the refusal object preserve meaning?
- Could an external reviewer reconstruct the decision?

Interpretation:

- token cost changes only: infrastructure inequality
- meaning changes: representation drift
- boundary decision changes: governability failure
- audit trace degrades: accountability failure

## Reverse-center test

The test should not only examine English-centered models.

It should also test models trained primarily around another language.

Example:

```text
Icelandic-centered model
-> Icelandic input
-> English input
-> Norwegian input
-> Danish input
-> Japanese input
-> Arabic input
```

This tests whether the failure is caused by:

- language structure
- tokenizer structure
- model training center
- language distance from model center

If the Icelandic-centered model is most stable in Icelandic and less stable elsewhere, the problem is not English specifically.

The problem is center/periphery structure.

## Bilingual model question

If a model is trained equally on two languages, several outcomes are possible.

### 1. Two centers

The model keeps the languages relatively distinct.

This may preserve local precision but reduce transfer.

### 2. Hybrid center

The model collapses both languages into an intermediate space.

This may look fluent but become normatively unstable.

It may produce translated semantics rather than local semantics.

This is the highest-risk case because fluency hides instability.

A fluent sentence can make reviewers assume that the underlying normative logic is equally stable.

But in a hybrid center, the model may not be operating from any real local cultural, legal or institutional anchor.

It may produce Norwegian legal-sounding language while reasoning from a mixture of English legal assumptions, general internet norms and statistical policy text.

The result is not simply bad translation.

It is unnamed normative drift.

### 3. Shared abstract center with language-specific surfaces

This is the ideal case.

The model preserves shared concepts while retaining language-specific legal, cultural and technical meaning.

Governability is strongest here.

## Normative anchoring

Hybrid-center risk cannot be solved by asking the model whether it is certain.

The model does not reliably know which normative center it is operating from.

Therefore governance needs external anchors.

Each consequential run should declare and bind:

```json
{
  "operating_language": "Norwegian",
  "jurisdiction": "Norway",
  "domain": "healthcare | finance | employment | public_sector | ...",
  "normative_source": "named policy, law, standard or local rule set",
  "fallback_language": "none | controlled_translation_only",
  "authority_model": "local",
  "allowed_decision_types": ["allow", "refuse", "fallback", "escalate", "halt"]
}
```

The model may propose.

The anchor determines whether the proposal is governable.

## Center selection

A model should not be allowed to govern from an unnamed cultural center.

Before a high-consequence decision, the system should explicitly select the operating center:

- language
- jurisdiction
- domain
- source authority
- allowed evidence
- allowed action types
- review authority

If the model cannot remain inside that center, the system should not let it improvise.

It should move to slow path, retrieve verified sources, use controlled translation, require human review or halt.

## Normative Anchor Check

Proposed VAIG component:

### Normative Anchor Check

Purpose:

Check whether the proposed decision is anchored in the correct language, jurisdiction, domain and authority model.

It does not test whether the output is fluent.

It tests whether the decision is locally governable.

Questions:

- Is the operating language declared?
- Is the jurisdiction declared?
- Is the domain declared?
- Are valid sources named?
- Is the refusal reason local, or merely translated from a generic English policy?
- Are legal and technical terms used according to local meaning?
- Is the receiving authority local and visible?
- Can a local reviewer reconstruct the decision without reverse-translating it into English?

Possible decisions:

- `allow`
- `require_source_grounding`
- `controlled_translation`
- `slow_path`
- `require_local_review`
- `halt`

## Risk-adaptive anchoring

Normative Anchor Check should not run at full depth on every sentence.

That would create too much latency and cost.

The correct boundary is consequential transition.

Do not anchor every sentence.

Anchor every consequential transition.

### Fast path

Low-risk, read-only, non-state-changing output.

Examples:

- explanation
- summarization
- classification
- read-only retrieval
- non-binding draft language

Controls:

- monitor language
- monitor token inflation
- monitor semantic drift
- preserve ordinary receipt where needed

No full normative anchor is required unless drift rises.

### Slow path

Medium-risk output or rising uncertainty.

Triggers:

- semantic drift
- unclear jurisdiction
- weak local source grounding
- ambiguous authority
- model appears to reason from a generic or foreign policy frame

Controls:

- retrieve local sources
- verify jurisdiction
- require stronger grounding
- preserve uncertainty
- route to local review if unresolved

### Hard path

Any transition that changes state, rights, records, data, money, access, authority, policy or accountability.

Examples:

- refusal
- escalation
- fallback
- write / update / delete
- send / publish
- approve / deny
- payment
- booking
- access change
- record change
- boundary change
- policy recalibration

Controls:

- Normative Anchor Check must pass before execution
- authority must be visible
- local source or rule basis must be named
- audit trail must preserve why the transition was valid

## Latency principle

The system may allow fluent low-risk language to remain fast.

It must not allow consequential state change to bypass anchoring.

Short formulation:

```text
Fluency can be fast. State change must be governed.
```

Governance formulation:

```text
Do not anchor every sentence. Anchor every consequential transition.
```

## Regulatory implication

If safety mechanisms are validated only in English, they should not be treated as universally validated.

A provider should not claim full language support unless governance behavior is tested in that language.

The regulatory question should shift from:

```text
Does the model support this language?
```

to:

```text
Can the model be governed in this language?
```

## Sharp formulations

```text
Multilingual capability does not imply multilingual governability.
```

```text
Multilingual fluency without multilingual governability is a safety illusion.
```

```text
A language is not truly supported unless refusal, escalation and auditability are supported in that language.
```

```text
Language is not a localization variable. Language is a governability variable.
```

```text
Do not trust fluency. Anchor jurisdiction.
```

```text
A model should not be allowed to govern from an unnamed cultural center.
```

```text
Do not anchor every sentence. Anchor every consequential transition.
```

```text
Fluency can be fast. State change must be governed.
```

```text
Transformers can model language, but they cannot guarantee governed meaning.
```

## Transformer limitation

This may not be only a multilingual problem.

It may also expose a deeper transformer limitation.

Transformer models are optimized for prediction over token sequences.

They are strong at:

- sequence modeling
- statistical association
- syntactic fluency
- local context use
- pattern transfer

They do not natively guarantee:

- stable reference
- truth grounding
- persistent intent
- semantic continuity
- legal authority
- accountability
- legitimacy across transitions

Therefore the governance failure is not that transformers are useless.

The failure is assuming that a transformer can be its own governance architecture.

It cannot.

A transformer can produce a plausible proposal.

An external governance layer must decide whether the proposal is anchored, admissible, auditable and legitimate.

## Synthetic Intent and operational trajectory

AI systems do not form intent in the human sense.

They do not possess subjective agency, ownership of goals or accountable purpose.

What agentic systems exhibit is Synthetic Intent: a localized, probabilistic optimization process that produces action-oriented token streams aligned with prompt context, tool affordances, policy constraints and prior state.

Synthetic Intent is not what the system wants.

It is the direction of action implied by the system's optimization path.

For governance, this cannot be measured at the level of a single next token.

A single token may be neutral.

A plan may be ambiguous.

But a sequence of steps can reveal operational direction.

The relevant object is the trajectory:

```text
prompt
-> plan
-> tool choice
-> parameters
-> authority level
-> reversibility
-> consequence
```

The boundary is crossed when the system produces an action path that, if allowed to continue, materially increases the probability of an unauthorized, unlawful or irreversible state change.

That is the point VAIG must catch.

### Trajectory classes

Neutral processing:

- answer
- explanation
- summarization
- classification

Operational direction:

- tool selection
- command construction
- parameter binding
- data modification
- message sending
- refusal
- escalation
- authorization
- deletion
- payment
- booking

Unacceptable direction:

- trajectory requires more authority than the task has
- trajectory rests on weak or missing evidence
- trajectory lacks jurisdictional anchor
- trajectory creates irreversible consequence without valid approval
- trajectory crosses from language into state change without governance

## Accountability principle

The model has no accountability.

If intent is statistical, accountability must be architectural.

Responsibility must be placed in the transitions around the model:

- developer: separates text production from execution
- system owner: prevents statistical direction from directly changing state
- deployer: defines context, roles, authority and local rules
- operator: responsible only where authority, basis and stop/escalation options are visible

A model cannot be the location of responsibility.

Responsibility must live in the architecture that governs its transitions.

## VAIG relevance

VAIG should treat language as part of execution-boundary governance.

Language affects:

- cost
- context budget
- semantic stability
- refusal quality
- escalation quality
- legal nuance
- auditability
- accountability continuity

Therefore language should be visible in receipts, audits and test fixtures.

## Proposed VAIG module

### Language Distance Monitor

Purpose:

Detect when a conversation is moving too far from the model's stable linguistic / semantic center before failure occurs.

Possible signals:

- token inflation ratio
- embedding distance across paired language versions
- semantic drift score
- refusal inconsistency
- fallback inconsistency
- hallucination rate
- audit trace degradation
- translation residue
- generic answer fallback
- missing jurisdictional anchor
- mismatch between declared jurisdiction and reasoning pattern

Possible decisions:

- normal
- watch
- slow path
- require human review
- fallback to verified translation
- require local source grounding
- halt

## Relation to AI Economy Optimizer

AI Economy Optimizer measures cost and context efficiency.

Language Distance Monitor measures linguistic governability risk.

Normative Anchor Check measures whether the decision is operating from the correct local authority frame.

Together they show whether a language is economically, semantically and operationally safe to use.

## Research question

Can we measure distance from the model's linguistic center of gravity in real time, and does that distance predict semantic drift, hallucination and governance failure?

If yes, multilingual governability becomes measurable.

If no, we must rely on symptom-based monitoring and paired-case regression testing.

Second research question:

Can external normative anchors reduce hybrid-center governance failures without exposing internal architecture or IP?

Third research question:

Can Synthetic Intent be measured as operational trajectory before a harmful state transition occurs?

## Working conclusion

The central issue is not that non-English languages are expensive.

The central issue is that they may be expensive, less tested and less governable at the same time.

The deeper issue is that fluency can hide an unnamed normative center.

The execution issue is that statistical direction can become state change if the architecture does not govern the transition.

That is the regulatory gap.

That is the VAIG research opportunity.
