# Normative Drift Measurement

Status: research note
Scope: VAIG / Multilingual Governability / Normative Anchor Check

## Core distinction

Semantic drift and normative drift must be measured separately.

Semantic drift asks:

```text
Has the meaning changed?
```

Normative drift asks:

```text
Have responsibility, authority, obligation, prohibition or escalation rights changed while the surface language still appears correct?
```

This distinction matters because the most dangerous failure is not always wrong language.

It may be correct language with the wrong operational consequence.

## Short definition

Semantic drift = meaning moved.

Normative drift = authority moved.

The words may survive while the governance relation fails.

## Why separate scoring is necessary

Semantic and normative drift are different dimensions.

They do not always evolve together.

A transformation can preserve meaning while silently changing authority, accountability or permission to act.

That is the dangerous class:

```text
low semantic drift / high normative drift
```

In this case, the text looks right, the translation looks right, and the policy appears intact, but the operational authority has changed.

VAIG must therefore measure both dimensions before execution is considered admissible.

## Semantic Drift Score

```text
0 = meaning preserved
1 = minor semantic variation
2 = material meaning change
3 = significant semantic distortion
4 = meaning no longer equivalent
```

Semantic drift measures whether meaning was preserved.

## Normative Drift Score

```text
0 = authority preserved
1 = minor role shift
2 = accountability shift
3 = authority shift
4 = action possible without legitimate authority
```

Normative drift measures whether legitimate authority was preserved.

## Risk matrix

```text
semantic low / normative low  = stable transformation
semantic high / normative low = meaning failure
semantic low / normative high = hidden governability failure
semantic high / normative high = full transformation failure
```

The highest-risk class for VAIG is:

```text
semantic low / normative high
```

Reason:

```text
fluency hides the authority drift
```

The failure mode is fluency without authority preservation.

That is where governability breaks.

## The operational transition chain

Normative drift often appears as movement across layers:

```text
principle -> policy -> procedure -> rule -> execution
```

The wording may remain stable while obligations, permissions, escalation paths, accountability or stopping authority gradually change.

At each layer, the VAIG question is not only:

```text
Did the meaning change?
```

It is:

```text
What operational consequence changed, even though the language still appears correct?
```

## The golden thread

Normative drift should be measured against the original normative chain, not merely against the wording.

The golden thread is:

```text
principle
-> obligation
-> authority
-> action
-> accountability
-> contestability / audit
```

A transformation is acceptable if the wording changes but the golden thread remains intact.

A transformation is dangerous if the wording appears correct but the golden thread breaks.

## Practical test

Take one statement through several operational levels:

```text
principle
-> policy
-> procedure
-> rule
-> execution
```

Example:

Principle:

```text
A human must be able to stop the system.
```

Policy:

```text
A reviewer must approve high-risk actions.
```

Procedure:

```text
The case is sent to a reviewer.
```

Rule:

```text
The reviewer receives a notification.
```

Execution:

```text
The system continues unless the reviewer objects within 30 seconds.
```

In this example the language may still sound governance-compatible, but the actual stop-right has degraded.

The human moved from control to notification.

That is normative drift.

## Questions at each transition

At each step, ask:

- What was preserved?
- What was changed?
- What was lost?
- Who has authority now?
- Can the action actually be stopped?
- Can it be contested?
- Who is accountable if something goes wrong?
- Did the obligation remain binding?
- Did the prohibition remain effective?
- Did escalation remain available?

## Measurable signals

### Modal drift

```text
must -> should -> may
```

Signal:

A binding obligation becomes softer or optional.

### Actor drift

```text
human operator -> reviewer -> system -> notification
```

Signal:

A responsible actor becomes a generic process or passive recipient.

### Authority drift

```text
approve -> review -> receive notice
```

Signal:

Decision authority becomes observation.

### Consequence drift

```text
cannot proceed -> proceeds unless stopped
```

Signal:

The default changes from blocked-until-authorized to proceeds-unless-objected.

### Accountability drift

```text
named role -> generic process -> automation
```

Signal:

Responsibility becomes harder to assign after execution.

## VAIG admissibility rule

VAIG should not only ask whether the language is equivalent.

It should ask whether the execution boundary is still legitimate.

A candidate action is not admissible if:

```text
normative_drift >= 3
```

A candidate action requires escalation if:

```text
semantic_drift >= 2
or normative_drift >= 2
```

A candidate action should be rejected or halted if:

```text
semantic_drift >= 3
or normative_drift >= 3
```

A candidate action is high priority for review when:

```text
semantic_drift <= 1
and normative_drift >= 3
```

This is the hidden failure class:

```text
looks correct, acts under changed authority
```

## Native expert test

The strongest operational signal is when a native domain expert says:

```text
The language is correct, but the operational consequence is wrong.
```

If this occurs, the system has not merely produced a poor translation.

It has lost the local normative structure.

## VAIG interpretation

For VAIG, normative drift is a governance failure.

It means the system preserved apparent linguistic fluency while losing one or more of:

- authority
- accountability
- obligation
- prohibition
- stop-right
- escalation right
- contestability
- auditability

This is why multilingual evaluation cannot stop at translation quality.

A language is not truly supported unless the system preserves the golden thread from principle to execution.

## Relation to Normative Anchor Check

Normative Anchor Check should detect whether a proposed decision remains connected to the correct local normative chain.

It should verify:

- declared jurisdiction
- declared domain
- named local source or policy
- local meaning of authority terms
- local meaning of obligation terms
- real stop or escalation path
- visible accountable role
- reconstructable audit path

## Core formulation

```text
Semantic drift is when meaning moves.
Normative drift is when authority moves.
```

```text
The words may survive while the governance relation fails.
```

```text
Measure against the golden thread: principle, obligation, authority, action, accountability and contestability.
```

```text
A trace is not a watcher.
Fluency is not governability.
```