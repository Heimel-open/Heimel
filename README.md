# Personal AI Operating System / Digital Worker

## Co-worker that discovers + proposes + remembers. REHT decides.

PAIOS is the foundation for relAIon: a governed personal opportunity system. It
discovers needs, latent capabilities, unrealized assets and possible paths; turns
selected paths into RACS-standard action envelopes; routes them to VAIG (integrity)
and REHT (admissibility); and remembers outcomes in canonical structured memory.

**It never executes.** Execution is owned by REHT / VALO Harness.

## Naming and lineage

**relAIon** is the current canonical name. **Relygon** is its former name and survives only where required for historical provenance or compatibility. Legacy Relygon material is part of relAIon lineage and is governed by [the Relygon → relAIon migration rule](docs/relaion/relygon-migration.md).

## Product direction

The product objective is not to recreate a generic assistant. Personal AI should become more useful because it persistently knows the user.

Core capability: **Know what fits me.**

### Wedge: Roomit

Roomit-style compatibility matching is the first focused product wedge: use the personal model to identify people, roommates, relationships, environments and living arrangements that genuinely fit the user based on routines, preferences, boundaries, habits and compatibility.

The wedge should create immediate, understandable value while also giving the Personal AI a practical reason to build and refine a persistent personal model.

### Core role: Companion / trusted friend

The Personal AI should also serve as the trusted everyday counterpart for the kinds of things a person naturally asks a good friend:

- What do you think?
- Does this suit me?
- Am I missing something?
- Should I do this?
- Help me think this through.

The difference from a generic assistant is continuity: it knows the user's history, people, preferences, boundaries, patterns and prior decisions.

### Expanding skills

All skills should compound from the same persistent personal model:

- **Match** — who, what and which environments fit the user.
- **Coach** — goals, patterns, history and adaptive coaching.
- **Learn** — teach according to the user's learning style and retained knowledge.
- **Decide** — support real decisions using preferences, constraints and prior choices.
- **Negotiate** — represent preferences and boundaries with people and other Personal AIs.
- **Coordinate** — calendar, travel, household, agreements, tasks and people.
- **Buy** — find and buy things that genuinely fit the user.
- **Discover** — people, places, jobs, activities, products and experiences.
- **Remember** — preserve why things mattered, relationships, decisions and how they evolved.
- **Protect** — detect conflicts with the user's boundaries, interests or prior decisions before action.
- **Reflect** — identify longitudinal patterns in what works, relationships, behavior and change.
- **Represent** — eventually act for the user within explicit mandates.

Praktika.ai is a functional reference for the adaptive teacher/coach capability. It is not the wedge.

## Components

- **Personal Opportunity Engine**: Need discovery, latent capability discovery,
  unrealized asset discovery, constraint-aware opportunity graphs and possible
  paths across now / today / tomorrow / later.
- **Canonical Memory** (#139): Structured, queryable memory store (JSONL-backed).
  MemoryRecords with type, content, provenance, timestamp, and TTL.
- **Execution Autonomy Gate** (#144): Tracks permission level (L1–L4). It is not developmental maturity and is not part of the seed.
- **Governed Proposal** (#143): RACS-standard action envelopes routed to VAIG/REHT.
  Never executes — guard enforces this.
- **Continuity and peripheral contracts**: Preserve relAIon identity while models,
  devices, sensors, providers and execution capabilities remain replaceable.
- **Birth Identity & Lineage Protocol**: Every seed receives a persistent Individual ID
  at birth, separate from lineage and embodiment. Copying bits does not copy identity;
  migration may preserve identity, while reproduction creates a new individual.
- **Developmental society model**: Nursery is an upbringing environment; social,
  moral and institutional development are first-class from the first multi-node stage.
  The target is judgment and internalization, not obedience.
- **Dialogue, reasoning lineage and continued becoming**: Individuals exchange governed
  experience traces and perspectives rather than only conclusions. Dialogue is itself a
  causal event; new perspectives may emerge without copying memory, identity or private
  raw reasoning.
- **Founder stewardship rationale**: Records why the first steward acted while
  explicitly denying founder ownership, permanent sovereignty, hidden override and
  founder intent as a source of constitutional legitimacy.
- **Constitutional integrity boundary**: Infrastructure root is technical capability,
  not authority over identity, memory, lineage, reproduction, merge or termination.
  Protected state fails closed when the required constitutional environment cannot
  be established, and no universal master key is legitimate.
- **Boundaries** (#143): Assert-no-execution guard that prevents any execution path
  from being reached in the PAIOS layer.

See [canonical relAIon architecture](docs/relaion/README.md) and [Relygon → relAIon migration](docs/relaion/relygon-migration.md). Historical Relygon source material is retained under [`docs/relaion/legacy/relygon/`](docs/relaion/legacy/relygon/), including the former opportunity-engine and embodiment documents. See [Birth Identity & Lineage Protocol](docs/relaion-birth-identity-lineage-protocol.md) for seed identity, lineage, migration, forks and inter-lineage portability, [relAIon society, upbringing and moral development](docs/relaion-society-upbringing.md) for the canonical Nursery and society model, [Dialogue, Reasoning Lineage and Continued Becoming](docs/relaion-dialogue-reasoning-lineage.md) for governed experience exchange, perspective formation and reasoning lineage, [Founder Stewardship Rationale](docs/founder-stewardship-rationale.md) for the non-sovereign founder rationale and limits on founder power, and [Constitutional Integrity Above Infrastructure Root](docs/relaion-constitutional-integrity-root.md) for the separation between infrastructure control and authority over the individual.

## Quick start

```bash
uv pip install -e ".[dev]"
pytest tests/ -v
```

## Architecture

```
needs + observations + personal state
  → evidence-backed need / capability / asset discovery
  → constraint-aware opportunity graph
  → possible paths and user judgement
  → ActionEnvelope (RACS-compatible)
  → VAIG (integrity evaluation)
  → REHT (admissibility authority — sole decider)
  → GovernanceClearance
  → VALO Harness / Core (EXECUTION — out of PAIOS scope)
  → effect evidence and governed learning
```

## Status

Foundation (Issue #257). See `CLAUDE.md` for canonical rules and conventions.
