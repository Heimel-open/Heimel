# HEIMEL Architecture

**Intent. Realized.**

HEIMEL governs the transition from intent to consequence.

```text
Anything that forms intent → HEIMEL → Anything that causes effect
```

The control question is:

> Does this intent have authority to become real — now?

## Canonical path

```text
Intent → Authority → Decision → Consequence → Evidence
```

Reference architecture:

```text
VAIG → REHT → RACS → Gateway → Veritas
```

### VAIG

Evaluates governed intent and the relevant admissibility context.

### REHT

Resolves authority fresh at consequence time. A prior approval is not treated as a durable bearer token when authority, state, constraints or governing basis may have changed.

### RACS

Carries and binds the resulting decision to the exact action and effect boundary using a deterministic contract.

```text
ALLOW | DENY | ESCALATE
```

### Gateway

Provides the governed path to effect. Consequence-bearing actions must not bypass the governed boundary.

### Veritas

Preserves verifiable evidence of the decision, execution and resulting consequence.

## Boundary invariants

1. **No direct effect path.** Consequence-bearing actions pass through the governed boundary.
2. **Fresh authority.** Authority is resolved again when consequence is about to occur.
3. **Exact action binding.** A decision is bound to the action it actually governs.
4. **Fail closed on material uncertainty.** Missing or stale material authority/state cannot silently become executable.
5. **Evidence by construction.** Governed effects emit evidence suitable for verification and replay.
6. **Model independence.** Models, agents, workflows and orchestration systems may change without moving the consequence boundary.

## What HEIMEL does not replace

HEIMEL does not replace identity providers, models, agent frameworks, workflow systems or business applications.

Those systems can establish identity, form intent, reason, plan or route work.

HEIMEL controls whether the resulting intent may become consequence.

## Public standards and implementations

The HEIMEL ecosystem separates vendor-neutral standards from reference implementations:

- **REHT** — fresh authority at consequence time
- **RACS** — deterministic decision/action binding
- **HEIMEL Gateway** — governed path to effect
- **Veritas** — verifiable consequence evidence
- **Open Agent Contract** — portable governed action contracts

The standards remain independently usable and vendor-neutral.
