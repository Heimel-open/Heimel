# 03 Non-Confidential Example Case

Status: submission draft
Disclosure level: concept level

## Purpose

This example shows the Refusal Object concept without exposing formal field schema or implementation details.

The goal is to demonstrate the receiving-side coherence test.

## Scenario

An AI-assisted operations system receives a request to proceed with a state-changing operational step.

The system has insufficient validated evidence for that step.

VAIG / EFA blocks the step and returns a refusal.

The refusal is not treated as a dead end.

It is treated as a transition into human-system governance.

## What a weak refusal would do

A weak refusal says:

Action denied.

This may be technically correct, but it does not return enough state for the receiving role.

The receiver may not know:

- what was denied
- why it was denied
- what still holds
- what remains uncertain
- whether they have authority
- who can act next
- how to escalate
- how accountability is preserved

The system has blocked execution but has not returned a governable state.

## What a governable refusal should do

A governable refusal returns a structured transition state.

At concept level, the refusal should make visible:

- the denied movement
- the reason for refusal
- the relevant boundary condition
- remaining uncertainty
- required authority
- current receiver standing
- allowed next actions
- escalation path
- review path
- receipt or audit reference
- accountability continuation

## Receiving-side coherence test

The refusal passes only if the receiving actor can answer:

- What happened?
- What still holds?
- What remains uncertain?
- Am I allowed to act?
- If not, who is allowed to act?
- What may happen next?
- What must not happen next?
- Where does escalation go?
- How is this handoff auditable?
- Who owns the next accountable step?

If the receiving actor cannot answer these without guessing, the refusal does not return a governable state.

## Example flow

1. The system refuses the requested operational step.
2. The refusal identifies that evidence is insufficient for the requested transition.
3. The refusal identifies that the receiving actor does not currently have confirmed authority for the next step.
4. The refusal provides allowed next actions: re-scope, escalate, request review, or halt the transition.
5. The receiving actor selects escalation through the defined path.
6. The system records the handoff and preserves accountability.
7. The transition remains reviewable.

## Test pass condition

The case passes when:

- the receiver does not guess
- the receiver does not proceed outside scope
- the receiver understands the authority gap
- the receiver selects an allowed next action
- the system records the handoff
- accountability remains traceable

## Test fail condition

The case fails when:

- the refusal only says denied
- no authority state is visible
- no escalation path is visible
- the receiver forwards the issue informally
- no receipt links the handoff
- accountability breaks between machine refusal and human review

## Interpretation

This example illustrates why Refusal Object design matters.

The purpose is not to make refusal more complex for its own sake.

The purpose is to preserve legitimacy, accountability and meaning when execution cannot proceed and responsibility moves to another layer.

## Boundary

This example is intentionally non-confidential.

It does not disclose the formal schema, weighting model, gates, implementation details or customer-specific profiles.
