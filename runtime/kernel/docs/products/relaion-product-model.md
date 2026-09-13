# relAIon product model

## Canonical promise

> **You connect to relAIon. relAIon connects you to the world.**

This is both the product promise and the architectural rule.

A person establishes one governed relationship with relAIon. relAIon then mediates access to devices, capabilities, services, agents, people, compute and networks without requiring the person to manage each relationship as an independent control plane.

## Three product layers

### relAIon Node

The software installed on a device or exposed through a supported surface.

On first launch the node inventories the capabilities that can actually be realised on that surface and presents them as human scenarios rather than infrastructure terminology. Examples include local reasoning, files, browser activity, calendar, camera, microphone, notifications and communication with other trusted nodes.

Enabling or installing a capability makes it available. It does not grant Handlingsrett to use it for every purpose or consequence.

### relAIon

The person's persistent intelligence and control plane spanning their authorised nodes.

relAIon holds orchestration, governed personal context, capability discovery and routing, node relationships and the interface to VALO consequence authorization. A PC relAIon and phone relAIon are therefore not separate assistants. They are nodes belonging to one relAIon.

### relAIon Network

The optional capability fabric beyond the capabilities already present on a node.

A user may connect a node to the relAIon Network to discover or obtain additional:

- capabilities
- skills
- connectors
- models
- specialist agents
- workflows
- voices
- avatars
- compute
- services

The network is not merely an app store. Every offered object must expose a machine-readable capability contract covering at minimum provider/provenance, version, required data and access, execution location, possible effects, cost/resource requirements, evidence obligations and revocation/update semantics.

Network availability is not authority. Installation is not authority. Discovery is not authority.

## relAIon as capability mediation layer

relAIon must be useful before every application, service and device has a dedicated API, MCP server or native integration.

The installed relAIon Node therefore acts as a mediation layer between human intent and whatever interaction surfaces already exist on that device. It converts available routes into normalized capabilities while keeping the user-facing capability stable even when the underlying implementation changes.

Canonical route preference:

1. native capability/API
2. MCP, connector or other explicit machine interface
3. operating-system intent/action surface
4. semantic UI automation, including accessibility trees or browser DOM where permitted
5. human-equivalent input such as mouse, keyboard, touch, typing and scrolling as a constrained fallback where the platform permits it

The fallback route must never become the capability abstraction. A capability is expressed in terms of the intended effect, for example `calendar.create_event`, `message.send` or `document.save`. Whether that capability is realised today through UI automation and tomorrow through a native API is an implementation detail of the capability route.

This lets relAIon bootstrap useful capability from software that was designed primarily for human operation, without waiting for every vendor to expose a machine-native interface. As formal APIs and integrations become available, relAIon should migrate to the stronger route without changing the user's intent model, capability contract or governance boundary.

Every route is still subject to the same rule: interface access is not Handlingsrett. Accessibility permission, browser permission, an App Intent, an MCP tool or possession of an API credential only establishes that a route exists. The exact proposed effect must still be normalized and freshly authorized at consequence time before invocation.

Canonical effect path:

`human intent -> relAIon -> capability abstraction -> best available route -> VALO fresh authorization -> effect -> receipt`

relAIon is therefore a transitional middleware for the world as it exists now and a stable capability control plane for the machine-native world as it develops.

## Visible worker and operational-state surface

relAIon should expose agentic work in the same way conversational systems expose a high-level "thinking" state, but for real-world action the useful object is operational state rather than private model chain-of-thought.

Each relAIon agent or worker SHOULD emit a live, user-readable execution trace covering at minimum:

- current objective
- current worker/agent
- selected capability
- active node or surface
- selected capability route
- current operational phase
- pending consequence, if any
- authorization state
- handoffs to other workers or nodes
- result state
- receipt/evidence availability

Example phases include: planning, discovering capability, checking access, waiting for authorization, opening an application, reading, preparing a change, invoking, verifying, blocked, completed and failed.

This trace is a first-class interaction primitive. It must not depend on a graphical avatar. A task panel, compact status view, timeline, enterprise operations console or accessibility-oriented representation can all render the same underlying event stream.

An optional visible-worker mode may render the trace as an on-screen relAIon worker or avatar that visibly opens applications, navigates interfaces, types, clicks, hands work to another node, pauses for approval and reports completion. The visualization is therefore an observer surface over governed execution, not decoration.

The canonical observable path is:

`intent -> worker -> selected capability -> active surface -> pending effect -> authorization state -> action -> verification -> receipt`

Operational-state visibility supports Human-in-the-Lead by making agentic work visible, interruptible, attributable and replayable without exposing private model reasoning. Users should be able to understand what is happening, intervene where permitted, inspect blocked or escalated actions and verify what happened afterward.

relAIon should support at least two presentation modes over the same execution state:

1. quiet/background mode, where permitted and authorized
2. visible-worker mode, where current work is continuously rendered to the user

The execution trace is the product primitive. The avatar is one optional visualization of it.

## Transparency as a trust invariant

Transparency is part of the relAIon trust architecture, not an optional UX treatment.

The governing rule is:

> **Nothing hidden that materially affects the user.**

For every meaningful capability, relAIon SHOULD make it possible for the user to determine, in human-readable form:

- what the capability can sense, read or access
- why that access is being used for the current objective
- which node, worker and provider are involved
- where processing occurs: on-device, on another trusted node or remotely
- what information is retained and for how long
- what information is transmitted and to whom
- what consequences the capability may create
- what Handlingsrett currently permits
- what is waiting for authorization, denied or escalated
- what action actually occurred
- what evidence or receipt exists afterward

Ambient and sensing capabilities require especially explicit state. Listening, seeing, location sensing and background observation MUST NOT collapse into an opaque binary permission. The user-facing state should distinguish states such as local wake detection, active capture, local transcription, remote processing requested, retention, transmission and effect authorization.

A representative audio path may therefore be rendered as:

`listening locally -> wake detected -> local transcription -> context used -> raw audio discarded`

or, when a stronger consequence is proposed:

`audio captured -> remote processing requested -> Handlingsrett required -> ALLOW/DENY/ESCALATE -> transmission/effect -> receipt`

Sensing does not imply authority to remember, transmit, infer, disclose or act. These are separate capabilities and consequences and SHOULD be governed independently.

Trust in relAIon should therefore be evidence-based rather than assertion-based. The user should be able to see what the system can do, see what it is doing, see what it did, inspect the mandate under which it acted and verify the resulting evidence.

Canonical trust relationship:

`capability visibility + operational transparency + fresh authority + evidence + verification -> defensible trust`

Trust scores, reputation and prior behavior may inform decisions, but they are indicators rather than proof. Consequential trust must remain grounded in observable state, explicit authority and verifiable outcomes.

## Hypothesis: a generative invariant for organized action

The recurring architecture across relAIon surfaces suggests a broader hypothesis, but this MUST be treated as a hypothesis rather than a conclusion.

The hypothesis is that a stable relational form may underlie organized action across materially different substrates and actors. The concrete realization may change, while a core structure remains recognizable.

A provisional form is:

`possibility -> selected capability -> route -> authority -> consequence -> evidence -> new state`

The working claim is not that every system must use these labels, nor that this sequence is already proven to be universal. The claim to test is whether organized action can be represented without loss across different domains by preserving the same underlying relations even when the implementation changes.

Candidate domains include:

- a person using a tool
- an AI agent acting through software
- multiple cooperating agents or workers
- an organization acting through delegated roles
- a machine or robot interacting with a physical environment
- a distributed network coordinating capabilities across nodes
- public or regulated systems producing consequential decisions or effects

The key distinction is between invariant form and variable realization:

> **The form may be invariant while the realization remains variable.**

relAIon, VALO, a phone, a browser worker, an enterprise process or a future autonomous machine could then be different realizations of the same deeper organization of action rather than unrelated architectures.

This hypothesis is only useful if it is falsifiable. The research task is therefore to search deliberately for counterexamples: organized action systems in which the proposed structure cannot faithfully represent what actually occurs, or where one of the proposed relations is unnecessary, misleading or reducible to something else.

Evidence in favor would require the form to survive increasingly different domains without accumulating ad hoc exceptions. Evidence against would include domains that require fundamentally different primitives, ordering or causal relations.

Until such tests exist, this remains a research hypothesis:

**relAIon may be one realization of a more general generative invariant for organized action.**

## Canonical first-run flow

1. Install relAIon Node.
2. Establish node/device identity and bind it to the person.
3. Inventory the surface and discover locally realisable capabilities.
4. Present concrete scenarios: "This device can..."
5. Let the user enable selected local capabilities with least-necessary access.
6. Activate the mandatory VALO/Handlingsrett consequence boundary.
7. Offer optional connection to the relAIon Network.
8. Discover/install additional capabilities under explicit contracts.
9. For every effect: normalize -> fresh authorize -> invoke -> receipt.

## Architectural consequence

Models are providers, not relAIon. Operating systems are substrates, not relAIon. MCP, browsers, apps and APIs are capability surfaces, not relAIon.

The same logical relAIon can span Windows, Linux, macOS, Android, iOS/iPadOS, HarmonyOS/OpenHarmony, browser surfaces, MCP and future substrates.

The user connects to one governed personal control plane. That control plane connects outward to the world.
