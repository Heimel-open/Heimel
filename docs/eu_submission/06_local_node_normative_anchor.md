# Local-Node Authority Preservation Note

Status: submission support note

Disclosure level: concept level

Purpose: consolidate the Authority Visibility, normative drift, local-node topology and shadow IT argument for the EU AI Act submission package.

This note should be treated as a precision clarification inside the existing Governability Architecture framing.

It should not be presented as a new theory, a new control system, or a replacement for VAIG, EFA, MECHA, WHY Gate, RRP or WORM.

The primary submission point is the architectural principle.

Implementation patterns, including a possible Node-Level Normative Anchor Check, should remain secondary and reserved for later formalization.

## 1. Core problem

The current submission framing already separates the architecture correctly:

MECHA governs decision legitimacy.

VAIG / EFA governs execution legitimacy.

Governability Architecture governs transition legitimacy.

The Refusal Object makes blocked execution observable, auditable and contestable.

Authority Visibility prevents a receiving human from becoming a passenger.

The remaining problem is that Authority Visibility must be testable, not merely declared.

A human may be present.

A policy may exist.

A log may exist.

A refusal may be generated.

But the right to decide, challenge, stop, re-scope or escalate may already have moved.

That is the missing operational failure class.

## 2. Architectural principle

The governability requirement is:

Authority, accountability, contestability and stop-rights must survive to the point where consequence is committed.

This is the primary claim.

The implementation mechanism is secondary.

For the EU submission, the emphasis should remain on the principle and the topology implication, not on prescribing a specific protocol or check layer.

Core formulation:

Oversight must follow the consequence.

If the consequential transition occurs at the node, then authority preservation must be demonstrable at that boundary, not only in the central system.

## 3. Semantic drift versus normative drift

Semantic drift asks whether meaning survived the transition.

Normative drift asks whether legitimate authority survived the transition.

The dangerous case is not high semantic drift.

The dangerous case is low semantic drift combined with high normative drift.

Everything appears correct, yet the right to decide, challenge, stop or escalate has quietly moved.

Example:

Reviewer must approve.

becomes:

Reviewer is notified.

The language still sounds governance-compatible.

But the human has moved from control to observation.

That is not only a language failure.

It is a governability failure.

Working phrase:

Fluency without authority preservation.

## 4. Local-node topology as normative drift

The local-node problem is a topology form of normative drift.

Everything may appear compliant at the central level while authority has already shifted at the execution boundary.

Central policy may exist.

Central logging may exist.

Central human oversight may exist.

Central documentation may exist.

But if consequence is committed at a local node, then governance must be able to show that authority survived at that node.

The relevant question is not only:

Was the system governed centrally?

The relevant question is:

Was the consequential transition governed where it occurred?

## 5. Placement in chain

Current conceptual chain:

EvidenceCondition

Intent

VAIG Authorization

Action / Refusal

RRP

Accountability Thread

Receipt / WORM

Principle-level precision chain:

EvidenceCondition

Intent

VAIG Authorization

Authority Preservation at Execution Boundary

MECHA / Human Ownership

WHY Gate

Action or Refusal

RRP

Accountability Thread

Receipt / WORM

Short distinction:

VAIG asks whether the transition is admissible from the evidence and intent state.

Authority Preservation asks whether authority, accountability, contestability and stop-rights survived to the point of consequence.

MECHA asks who must own the decision.

WHY Gate asks whether the reason still holds at consequence commit.

RRP / WORM proves the refusal, escalation and accountability chain.

## 6. EU AI Act relevance

The strongest EU AI Act link is Article 14 / human oversight.

Human oversight is not real if the human is only notified.

It is real only if the human retains standing to authorize, stop, challenge, re-scope or escalate before consequence is committed.

The architecture should therefore support demonstrable authority preservation at transition time.

It also supports:

Article 9 / risk management:

Normative drift and local-node authority loss become defined transition risks.

Article 12 / logging and traceability:

The Refusal Object and receipt chain can preserve authority state and transition legitimacy.

Article 13 / transparency:

Deployers can see whether the human is controlling, reviewing, receiving notice or merely being logged.

Article 15 / robustness and cybersecurity:

A control is not robust if it sits outside the failure domain where the action happens.

Article 26 / deployer obligations:

Deployer-side monitoring and oversight require a way to preserve authority through handoff, refusal and escalation.

Core EU formulation:

Human oversight cannot be proven merely by showing that a human was present. It must be possible to show that human authority survived the transition to consequence.

## 7. Backup analogy

The backup example illustrates the same governability failure pattern.

A control can exist semantically while failing operationally.

Backup exists, but if it shares the same identity system, account, admin plane and blast radius as production, it is only a copy inside the same failure domain.

Human oversight has the same failure mode.

A human can be present, notified or logged, while real authority has already moved to the system.

Short analogy:

Backup without separate control is not backup.

Human oversight without separate authority is not oversight.

This should be used as an explanatory analogy, not as the main EU argument.

## 8. Local-node topology problem

The EU AI Act is largely framed around providers, deployers, AI systems, GPAI models, technical documentation, logging, risk management and human oversight.

That framing assumes the relevant AI system can be identified, documented, supervised and governed as a bounded system.

But AI deployment is moving from central network topology into distributed local-node topology.

The consequential transition may no longer occur only in a central cloud service.

It may occur on:

employee laptops

mobile phones

browsers

endpoint agents

operating system layers

Office tools

email clients

local assistants

browser extensions

BYOD devices

unapproved AI tools

embedded workflow agents

That changes the governance problem.

A provider may document oversight centrally.

A deployer may define policy centrally.

A human may formally be in the loop.

But the actual state-changing action may happen locally, at the node, before the central oversight layer can see, stop, challenge or escalate it.

That is the local-node problem.

Core sentence:

Oversight must follow the consequence.

If consequence is committed at the local node, then authority preservation must be demonstrable at the local node.

## 9. Evidence chain for topology shift

The movement from central network topology to local-node topology is supported by current infrastructure direction.

Hardware direction:

Endpoint hardware is becoming capable of local AI execution. AI workloads are increasingly supported on laptops, desktops, workstations, mobile devices and edge devices. New GPU and AI-PC generations, including Nvidia's Blackwell / RTX 50 direction, make local inference and endpoint AI increasingly practical.

Software and browser direction:

Compressed and smaller models make client-side inference more practical. Browser-side AI, including Google / Chrome / Gemini Nano-type patterns, turns the browser from a user interface into an AI execution environment.

Enterprise productivity direction:

Microsoft 365 Copilot places AI into Word, Excel, PowerPoint, Outlook, Teams and the Microsoft Graph context layer. That moves AI into documents, spreadsheets, presentations, meetings, workflow, organizational knowledge and the mail layer.

Mail-layer significance:

Email is not just communication. It is approval, delegation, escalation, legal notice, operational instruction and accountability trail. If AI enters the mail layer, it enters the authority layer.

Shadow IT direction:

Employees can use private AI accounts, browser extensions, personal devices, unapproved plugins, file-sync tools, cloud notebooks and automation apps. This creates parallel execution paths outside governed infrastructure.

Summary:

AI is moving into chips, browsers, Office tools, mail layers, endpoint agents and unmanaged employee devices. The execution boundary moves outward. Governance must follow it.

## 10. Shadow IT as invisible-node risk

Shadow IT makes the local-node problem worse.

The local-node problem is that AI execution moves to the edge.

Shadow IT adds that the organization may not know which edge exists.

Employees may bring or use:

private phones

personal laptops

browser extensions

unapproved AI tools

local agents

cloud notebooks

personal ChatGPT / Gemini / Claude accounts

automation apps

BYOD devices

unapproved plugins

file-sync tools

Then the governance chain breaks.

The company may have:

AI policy

human oversight

logging

approved tools

risk management

security controls

But the actual consequential transition happens outside that governed environment.

That means there may be:

no VAIG gate

no authority-preservation check

no MECHA handoff

no WHY Gate

no RRP

no receipt

no WORM log

no Authority Visibility

Shadow IT is the unregistered local-node problem.

A governed AI system may exist centrally, but employees may create parallel execution paths through unmanaged tools and devices.

In that topology, the formal governance architecture remains intact on paper while operational authority leaks into unobserved nodes.

This is normative drift by infrastructure.

Meaning and policy remain correct centrally.

Authority moves locally.

Short formulation:

Shadow IT turns local-node risk into invisible-node risk.

## 11. Optional implementation pattern

The following should be treated as one possible realization, not as the submission claim.

Possible name:

Node-Level Normative Anchor Check

or:

Local Execution Boundary Check

Question:

Before a local AI node changes state, sends, writes, deletes, approves, refuses, escalates or triggers an external action, can it show that the transition is occurring inside a governed node and that authority is preserved at the point of consequence?

This does not replace VAIG.

This does not replace MECHA.

This does not replace WHY Gate.

It is one possible way to make Authority Visibility topology-aware.

The implementation pattern should be reserved for later formalization.

## 12. Possible node-level schema for later work

This section is non-submission implementation material.

node_id

device_context

managed_node_status

approved_tool_status

transition_type

state_changing

tool_called

external_action

consequence_class

authority_required

authority_present

stop_right_present

escalation_path_present

human_review_required

normative_source

local_anchor_status

normative_drift_score

decision

receipt_id

Possible decision values:

allow

constrain

require_review

step_up

halt

## 13. Possible implementation rules for later work

If the node is unmanaged and the transition is consequential:

step_up or halt.

If authority cannot be proven at the node:

require_review or halt.

If stop-right is absent:

halt for high-consequence transitions.

If the action writes, sends, deletes, approves or changes access:

hard path.

If the node cannot produce a receipt:

do not treat the transition as governed.

Low semantic drift and high normative drift:

high-priority review.

These rules are not required for the main submission. They are a later protocol candidate.

## 14. Concrete case

A company deploys Microsoft 365 Copilot with policies, logging and human oversight.

At the same time, employees use personal AI tools and browser extensions to process emails, summarize contracts, draft replies, modify documents and prepare approvals.

A manager receives an AI-generated email summary.

A contract clause is softened.

A risk warning is omitted.

A reply is drafted and sent.

The organization's central AI policy still exists.

The official Copilot configuration still exists.

Human oversight still exists on paper.

But the actual transition happened in an unmanaged local node.

No one can prove:

which model touched the content

which authority was required

whether stop-right existed

whether escalation was available

whether the user had standing

whether the action was inside the governed system

whether the audit trail is complete

This is not simply shadow IT.

It is shadow authority.

## 15. Who does what

Elsa:

Owns the conceptual framing:

semantic drift

normative drift

authority preservation

golden thread

fluency without authority preservation

shadow authority

authority survival across topology shifts

Elsa's contribution is to define why this is not merely a cybersecurity issue. It is a governability issue.

Charles:

Validates the MECHA boundary.

The authority-preservation principle and any later node-level implementation must not decide who has legitimate authority.

MECHA still owns human mandate, decision legitimacy and accountability.

The authority-preservation layer only verifies whether that authority survived the transition and local execution boundary.

Njål / VALO:

Implements the technical layer later if needed.

Possible later tasks:

define schema

add local-node test cases

add shadow IT test cases

connect check to VAIG Authorization

connect output to Refusal Object

connect refusal to RRP

connect node receipt to WORM / central receipt chain

define hard gates for unmanaged consequential transitions

## 16. Submission posture

This should be presented as an architectural principle and topology implication for Authority Visibility and transition legitimacy.

Not as a new system.

Not as scope expansion.

Not as a general theory of morality, intent, truth or organizational legitimacy.

Not as an implementation prescription.

The submission already says Governability Architecture preserves authority, accountability, meaning and contestability across transitions.

The added point is:

That preservation must survive to the point where consequence is committed.

If the consequence is committed at the node, then preservation must be demonstrable at the node.

Possible implementation mechanisms can be reserved for later protocol work.

Final formulation:

A transition is only governable if authority, accountability, contestability and stop-rights survive at the point where consequence is committed.

If consequence is committed locally, governability must be demonstrable locally.

If the local node is unmanaged, human oversight cannot be proven.

## 17. Current conclusion

The EU AI Act problem is not only model risk.

It is execution-boundary risk in a distributed AI topology.

AI is moving into chips, browsers, Office tools, mail layers, endpoint agents and unmanaged employee devices.

That means governability must follow the consequence.

If authority cannot be shown at the local execution boundary, the transition is not governable.

This strengthens the existing Governability Architecture claim without adding a new theory.
