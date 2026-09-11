# HEIMEL

**Intent. Realized.**

HEIMEL is open infrastructure for the transition from intent to consequence.

```text
Intent → HEIMEL → Realized
```

Not every intent should become reality.

HEIMEL decides whether an action has the authority to become consequence — at the moment it matters.

## The question

> Does this intent have authority to become real — now?

HEIMEL sits immediately before effect:

```text
Anything that forms intent → HEIMEL → Anything that causes effect
```

## Core path

```text
Intent → Authority → Decision → Consequence → Evidence
```

The reference architecture is:

```text
VAIG → REHT → RACS → Gateway → Veritas
```

- **VAIG** evaluates governed intent.
- **REHT** resolves authority fresh at consequence time.
- **RACS** binds the decision to the exact action and effect boundary.
- **Gateway** provides one governed path to effect.
- **Veritas** preserves verifiable evidence of what became real.

## Start here

The canonical first demo is **Authority Drift**:

```text
08:00  mandate: $50,000
09:00  policy changes: $25,000
09:05  attempted action: $45,000
       ↓
       fresh authority check
       ↓
       DENY / ESCALATE
       ↓
       verifiable receipt
```

The point is simple: authorization must be resolved at the moment consequence is about to occur, not only when intent was formed.

## Open standards

HEIMEL is built around open, vendor-neutral contracts and standards.

- **REHT** — fresh authority at consequence time
- **RACS** — deterministic decision and action binding
- **Open Agent Contract** — portable governed action contracts

## Reference infrastructure

- **HEIMEL Gateway** — governed effect path
- **Veritas** — verifiable consequence evidence
- **SDKs and integrations** — connect models, agents, workflows, applications and devices

## Design principles

- **No direct effect path.** Consequence-bearing actions pass through a governed boundary.
- **Fresh authority.** Authority is resolved again when an action is about to become real.
- **Deterministic decision contract.** Decisions resolve to `ALLOW`, `DENY` or `ESCALATE`.
- **Evidence by construction.** Governed effects emit verifiable evidence.
- **Model-agnostic.** Models, agents and workflow systems may change; the consequence boundary remains governed.

## What HEIMEL is not

HEIMEL is not a model, an agent framework, an IAM replacement or a generic policy engine.

Identity can tell you who an actor is. A model can propose what to do. A workflow can route the work.

HEIMEL answers the question immediately before consequence:

**May this happen now?**

## Repository map

This repository is the public entry point for the HEIMEL open ecosystem.

Planned canonical structure:

```text
Heimel-open/
├── Heimel
├── reht-standard
├── racs
├── heimel-gateway
├── veritas
└── open-agent-contract
```

## Status

HEIMEL is under active development. Public repositories are being consolidated and aligned around a common open architecture, vocabulary and conformance model.

---

**HEIMEL**  
**Intent. Realized.**
