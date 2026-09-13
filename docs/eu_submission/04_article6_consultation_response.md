# 04 Article 6 Consultation Response

Status: submission draft
Disclosure level: concept level

## Target

Consultation comments on draft guidelines for high-risk AI system classification under the AI Act, with focus on Article 6 and Article 6(1)(a).

## Core comment

The classification question should follow the execution path, not only the product label.

AI systems are increasingly embedded inside closed ecosystems, productivity suites, operating systems, hardware layers, enterprise platforms and device environments.

In such settings, an AI system may be described as a general assistant, wrapper, embedded function or productivity feature, while still materially shaping execution paths inside regulated or high-consequence workflows.

The guidelines should clarify that classification and conformity assessment should consider whether the AI system can block, defer, escalate, authorize, re-scope or otherwise mediate an action path, not only whether it produces a final decision.

## Concern

A narrow reading may under-classify systems that are not presented as standalone high-risk AI products, but that still influence consequential operations through integration inside larger ecosystems.

Examples include:

- enterprise productivity ecosystems
- closed device ecosystems
- operating system assistants
- workflow automation tools
- AI-enabled office suites
- embedded AI functions in product chains

The risk is not only that the AI gives an answer.

The risk is that the AI changes what can happen next inside the system.

## Closed ecosystem concern

Closed ecosystems increase the governance challenge.

The AI system may operate across identity, access rights, files, messages, calendars, device functions, enterprise data, payment flows, health data, automation tools and third-party integrations.

A user or deployer may not experience the AI as a separate high-risk component.

They experience it as part of the environment.

For classification purposes, the relevant question should be:

What can the AI materially affect inside the ecosystem?

If the AI mediates execution, refusal, escalation or handoff in a regulated or high-consequence workflow, this should be visible in the classification analysis.

## Article 6(1)(a) relevance

Article 6(1)(a) is especially important where AI functions are integrated into products, enterprise systems or regulated product chains.

The guidelines should make clear that an AI component does not avoid scrutiny merely because it is embedded in a larger platform or marketed as support functionality.

The assessment should consider runtime function:

- Does the AI alter the execution path?
- Does it block, defer or escalate an action?
- Does it shape who may act next?
- Does it mediate handoff between automated control and human authority?
- Does it preserve auditability and accountability when action is refused or deferred?

Authority Visibility should be considered where human oversight depends on whether the receiving person has visible standing to authorize, challenge, stop, re-scope, escalate or review the transition.

## Refusal and escalation states

When AI systems mediate high-consequence workflows, refusal and escalation states should be treated as governance-relevant behavior.

A system that blocks or defers an action is not passive.

It has changed the transition path.

If the receiving human cannot understand what happened, what still holds, what remains uncertain, who has authority and what can legitimately happen next, the system may create operational ambiguity even when the refusal itself is correct.

## Proposed clarification

The final guidelines should clarify that, for systems within Article 6 and Annex III contexts, classification should consider whether the AI system materially mediates execution paths, including by blocking, deferring, escalating or re-routing actions.

Where such mediation occurs, the system should be assessed for whether it returns a governable state to the receiving role.

A governable state should preserve:

- authority
- auditability
- accountability
- contestability
- legitimate next action
- uncertainty visibility

## Suggested language

For AI systems embedded in products, enterprise platforms or closed ecosystems, assessment should consider the system's runtime role in the execution path, not only its product label or user-facing description.

Where an AI system blocks, defers, escalates, re-scopes or otherwise mediates an action in a regulated or high-consequence workflow, the assessment should consider whether the system preserves human authority, auditability, accountability and contestability across the transition.

A refusal or escalation should return a governable state to the receiving role, not merely a denial or generic warning.

## Relationship to Refusal Object

The Refusal Object is one proposed way to operationalize this requirement.

It treats refusal as a transition artifact rather than a terminal denial message.

The object makes visible:

- what was blocked
- why it was blocked
- what remains uncertain
- who has authority
- what can happen next
- where escalation goes
- what receipt preserves accountability

The detailed field schema and implementation model are reserved for the formal submission package and paper.

## Why this matters

Without this clarification, systems may be framed as low-risk assistance while still shaping regulated workflows through refusal, escalation, automation or handoff behavior.

This is especially relevant for closed ecosystems and enterprise platforms, where AI becomes part of the environment rather than a clearly separated tool.

The classification pathway should follow operational effect.

Not marketing category.

Not UI label.

Not whether the AI is standalone.

The key question is whether the AI materially shapes what happens next.

## Short formulation

The classification question should follow the execution path, not the product label.
