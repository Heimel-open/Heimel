<p align="center">
  <img src="assets/brand/heimel-readme-hero.jpg" alt="HEIMEL — Intent. Realized." width="620">
</p>

<p align="center"><strong>Intent. Realized.</strong></p>

<p align="center">
Open infrastructure for deciding whether intent has the authority to become consequence — at the moment it matters.
</p>

---

## The boundary

```text
Anything that forms intent → HEIMEL → Anything that causes effect
```

Not every intent should become reality.

HEIMEL sits immediately before effect and answers one question:

> **Does this intent have authority to become real — now?**

```text
Intent → Authority → Decision → Consequence → Evidence
```

## Run the live demos

**[Executable Authority — run the authority demo](https://reht.valoresearch.org/demos/executable-authority/)**  
Observe authority being resolved at the moment an action is about to become real — including what happens when authority changes after intent was formed.

**[EROC Replay — run the replay demo](https://reht.valoresearch.org/demos/eroc-replay/)**  
Inspect the evidence path by replaying a governed execution from its recorded artifacts.

A canonical Authority Drift scenario is:

```text
08:00   mandate                    $50,000
09:00   authority changes          $25,000
09:05   attempted consequence      $45,000
                              ↓
                     fresh authority check
                              ↓
                       DENY / ESCALATE
                              ↓
                      verifiable receipt
```

The earlier approval is not enough. Authority is resolved again when the action is about to become real.

## How HEIMEL works

```text
VAIG → REHT → RACS → Gateway → Veritas
```

| Component | Role |
|---|---|
| **VAIG** | Evaluates governed intent |
| **REHT** | Resolves authority fresh at consequence time |
| **RACS** | Binds the decision to the exact action and effect boundary |
| **Gateway** | Provides one governed path to effect |
| **Veritas** | Preserves verifiable evidence of what became real |

The decision contract is deliberately small:

```text
ALLOW | DENY | ESCALATE
```

## Open by design

The standards and reference contracts are open and vendor-neutral. Models, agents, workflows and applications can change without moving the consequence boundary.

**Core principles:** no direct effect path · fresh authority · deterministic decisions · evidence by construction · model-agnostic execution.

## Open ecosystem

```text
Heimel-open/
├── Heimel                 public entry point
├── reht-standard          fresh authority at consequence time
├── racs                   decision/action binding
├── heimel-gateway         governed path to effect
├── veritas                verifiable consequence evidence
└── open-agent-contract    portable governed action contracts
```

Public repositories are being consolidated into this structure. Links will become active here as each component is migrated and aligned.

## What HEIMEL is not

HEIMEL is not a model, agent framework, IAM replacement or generic policy engine.

Identity can establish who an actor is. A model can propose what to do. A workflow can route the work.

**HEIMEL decides whether it may become real.**

---

<p align="center"><strong>HEIMEL</strong><br>Intent. Realized.</p>
