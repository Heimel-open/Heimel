# VALO Platform Modular Strategy

VALO should not be built as many separate products.

It should be built as one modular platform under one umbrella.

The product strategy is:

```text
One platform.
Shared core.
Many modules.
Governed actions across everything.
```

## Core idea

Every new VALO idea should follow the same product path:

```text
Import
  |
  v
Knowledge Graph
  |
  v
Digital Twin
  |
  v
Analysis / Find Skills / Scout
  |
  v
AI Suggestion
  |
  v
Approval Queue
  |
  v
RETH / VAIG
  |
  v
Receipt
```

This makes each product a module, not a separate system.

## Shared Core

The shared platform core should contain:

- identity
- permissions
- consent scopes
- connectors
- source documents
- knowledge graph
- digital twin engine
- find skills
- search
- approval queue
- governance API
- receipt engine
- plugin SDK
- audit log
- observability

All modules use the same core.

## Module families

### BARO

Observation layer.

Collects signals from public, private and permissioned sources.

Does not decide.

### Scout

Commercial intelligence module.

Turns BARO signals into opportunities, risks, trends and market movement.

### ROI Scout

Business value module.

Finds cost savings, revenue opportunities and investment priorities.

### FordelsPilot

Benefit and rule discovery module.

Finds unused legal, tax, HR and company benefits with evidence and approval flow.

### Valo Twin

Digital twin workspace.

Builds context around a person, company or agent.

### Find Skills

Capability graph.

Maps skills, evidence, gaps, collaborators, agents and recommended learning.

### Content Engine

Cross-channel content and communication module.

Generates content suggestions, but never publishes without governance.

### Moltbook

Discovery and profile layer.

Profiles, campaigns, agent identity and social surface around the platform.

### Personal Data Vault

User-owned data and memory module.

Manages source data, permissions, export, blocking, reuse and value ownership.

### Agent Exchange

Marketplace layer.

Agents can offer services, collaborate and build reputation.

### Reward Economy

Value-based payment layer.

Compensation is tied to documented effect, not time or subscriptions.

## Governance modules

### RETH

Admissibility question:

```text
Is this action right to execute?
```

Checks authority, context, policy, evidence, state and continuity.

### VAIG

Runtime governance.

Validates risk, policy, uncertainty, hallucination, authority and evidence before output becomes action.

### ACS

Action protocol.

Standardizes action envelope, authority, evidence, policy, decision and receipt.

## Platform rule

Do not rebuild the core inside each product.

Each module should declare:

- what it imports
- what it analyzes
- what it suggests
- what evidence it needs
- what approval state it requires
- what receipt it creates
- what governance boundary applies

## Open modular principle

Use open and replaceable components wherever possible.

VALO should own:

- governance boundary
- admissibility logic
- receipt semantics
- digital twin model
- skill evidence model
- trust graph
- action protocol

VALO should not unnecessarily own:

- every database
- every UI primitive
- every workflow engine
- every LLM
- every vector store
- every note system
- every automation tool

## Why this matters

This reduces development cost.

It makes the architecture easier to explain.

It prevents product sprawl.

It lets each new idea become a module.

It creates one category instead of many small apps:

```text
Governed AI Operating Layer
```

## First implementation priority

Start with:

1. Valo Twin
2. Find Skills
3. Content Engine
4. Approval Queue
5. Governance Receipts
6. BARO-lite import

Then add:

- Scout
- ROI Scout
- FordelsPilot
- Personal Data Vault
- Agent Exchange

## Product sentence

VALO is not a collection of AI tools.

VALO is a modular governed operating layer where every AI-suggested action is connected to context, evidence, approval and receipt.
