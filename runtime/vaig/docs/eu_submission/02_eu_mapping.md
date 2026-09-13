# 02 EU Mapping

Status: submission draft
Disclosure level: concept level

## Purpose

This note maps the VAIG / MECHA / Governability framing to EU AI Act implementation concerns at a conceptual level.

It is not a legal opinion.

It is a technical governance contribution.

## Main relevance

The proposal is relevant where AI systems move from information output into consequential operation.

The core issue is transition legitimacy.

Governability concerns the preservation of authority, accountability, meaning and contestability across transitions.

At the concept level, the relevant transition is:

- evidence enters a system
- intent is formed or blocked
- an action is allowed or refused
- a human role receives the refusal
- review, escalation or recovery follows
- accountability must remain intact

The Refusal Object makes this transition visible.

Governability Architecture tests whether the transition remains legitimate.

## Compliance anchors

The proposal maps most directly to these compliance areas:

- risk management
- human oversight
- transparency
- technical documentation
- logging and record keeping
- conformity assessment
- post-market monitoring
- deployer accountability

These are the practical hooks for the Refusal Object and Authority Visibility.

The Refusal Object supports technical documentation, logging, traceability and post-incident review.

Authority Visibility supports meaningful human oversight by ensuring the person receiving a refusal has visible standing, authority path and next-action options.

Governability Architecture supports risk management by treating refusal, escalation and handoff as monitored transition states rather than informal messages.

## Human oversight

Human oversight is not satisfied by human presence alone.

A human can be in the loop without having authority to act.

Authority Visibility asks whether the receiving human has standing to authorize, challenge, stop, re-scope, escalate or review.

This supports meaningful human oversight because the system must show:

- who may act
- who may not act
- what can happen next
- where escalation goes
- how accountability is preserved

This is especially important where deployers must assign oversight responsibilities to competent and trained individuals with effective authority to perform those duties.

## Technical documentation

A high-consequence AI system should document not only model behavior, but also transition behavior.

For refusal and escalation, documentation should describe:

- what kinds of actions can be blocked or deferred
- what evidence or boundary conditions can trigger refusal
- how authority is surfaced to the receiving role
- how next actions are constrained
- how receipts and logs preserve the handoff
- how review or contestability is supported

This positions the Refusal Object as part of the technical documentation and governance evidence base.

## Traceability

A refusal should preserve enough state for later reconstruction.

The relevant trace is not only model input and output.

The relevant trace includes:

- what was blocked
- why it was blocked
- what condition triggered refusal
- what uncertainty remained
- who received the transition
- what next step was allowed
- what receipt preserved the handoff

## Auditability

The Refusal Object supports auditability by treating refusal as a structured event rather than an informal message.

A review should be able to reconstruct whether the refusal returned a governable state to the receiving role.

If the receiver could not identify authority, uncertainty, next action or accountability path, the transition was not operationally auditable in a meaningful way.

## Risk management

Risk is not only in the proposed action.

Risk also appears when a correct refusal creates ambiguity.

A refusal that blocks execution but leaves the receiver unsure about authority or next action can increase operational risk.

Governability Architecture treats that handoff as a monitored transition.

## Conformity assessment relevance

For systems on a high-risk pathway, conformity assessment should not only examine intended purpose, model properties and user documentation.

It should also consider runtime transition behavior.

Where the AI system blocks, defers, escalates, re-routes or otherwise mediates action, the assessment should consider whether the system returns a governable state to the receiving role.

This is particularly important for systems embedded in enterprise platforms, product chains and closed ecosystems.

## Post-market monitoring

Post-market monitoring should include transition failures.

Examples of transition failures:

- refusal without authority visibility
- escalation without owner
- handoff without receipt
- receiver unable to determine allowed next action
- accountability break between automated refusal and human review

These events should be treated as operational governance signals, not just UI issues.

## High-risk AI systems

High-risk systems require stronger transition handling because consequences may continue after a refusal.

In these contexts, a refusal should not simply stop a step.

It should preserve a controlled path for:

- escalation
- human review
- recovery
- contestability
- receipt-linked accountability

## Accountability

Accountability can fail during handoff.

The proposed model asks whether responsibility survives the transition between machine-side refusal and human-side decision.

This is the key bridge between VAIG / EFA and MECHA.

VAIG / EFA governs execution legitimacy.

MECHA governs decision legitimacy.

Governability Architecture governs transition legitimacy.

It tests whether accountability survives the movement between them.

## Contribution to EU implementation discussion

This contribution offers a bounded way to operationalize transition governance without expanding AI governance into an unbounded theory of intent, truth or organizational legitimacy.

The governance object is not intent itself.

The governance object is the observable transition between states.

That transition becomes governable only when it is observable, challengeable, auditable and attributable.

## Use of secondary compliance guides

Commercial compliance guides are useful for language and structure, especially around risk management, documentation, human oversight, logging, conformity assessment and post-market monitoring.

They should not be treated as primary authority in the submission.

Primary references should remain EU sources, the AI Act text and the relevant Commission consultation material.

## Suggested framing for submission

This should be presented as:

A technical governance contribution for operational human oversight, refusal handling, traceability and accountability preservation in high-consequence AI systems.

It should not be presented as:

- a general theory of AI morality
- a claim to determine truth
- a replacement for legal accountability
- a complete implementation specification

## Reserved details

The following should remain in the private submission package or subsequent paper:

- formal field schema
- weighting model
- gates
- test fixtures
- concrete implementation details
- customer-specific review profiles
