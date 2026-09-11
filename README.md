<p align="center">
  <img src="assets/brand/heimel-readme-hero.jpg" alt="HEIMEL — Intent. Realized." width="620">
</p>

<p align="center"><strong>Intent. Realized.</strong></p>

<p align="center">
Open infrastructure for deciding whether intent has the authority to become consequence — at the moment it matters.
</p>

<p align="center">
<a href="https://reht.valoresearch.org/demos/executable-authority/"><strong>Run the demo</strong></a>
&nbsp; · &nbsp;
<a href="docs/ARCHITECTURE.md">Architecture</a>
&nbsp; · &nbsp;
<a href="docs/DEMOS.md">All demos</a>
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

## Run it

### Executable Authority

**[Run the live authority demo →](https://reht.valoresearch.org/demos/executable-authority/)**

Observe authority being resolved at the moment an action is about to become real — including what happens when authority changes after intent was formed.

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

### EROC Replay

**[Run the replay demo →](https://reht.valoresearch.org/demos/eroc-replay/)**

Inspect the evidence path by replaying a governed execution from its recorded artifacts.

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

[Read the architecture →](docs/ARCHITECTURE.md)

## Open standards and infrastructure

The standards and reference contracts are open and vendor-neutral. Models, agents, workflows and applications can change without moving the consequence boundary.

Current public sources are being consolidated under `Heimel-open`. Until the migration is complete, the canonical public repositories remain available at their existing locations:

- **[REHT Standard](https://github.com/nsolland/reht-standard)** — fresh authority at consequence time
- **[RACS](https://github.com/nsolland/Racs)** — deterministic decision/action binding
- **[VALO Gateway](https://github.com/nsolland/valo-gateway)** — current public reference enforcement infrastructure; moving toward HEIMEL Gateway
- **[Veritas](https://github.com/nsolland/Veritas)** — verifiable consequence evidence
- **[Open Agent Contract](https://github.com/nsolland/open-agent-contract)** — portable governed action contracts

Target structure:

```text
Heimel-open/
├── Heimel                 public entry point
├── reht-standard          fresh authority at consequence time
├── racs                   decision/action binding
├── heimel-gateway         governed path to effect
├── veritas                verifiable consequence evidence
└── open-agent-contract    portable governed action contracts
```

## Design principles

**No direct effect path · Fresh authority · Exact action binding · Fail closed · Evidence by construction · Model independence**

## What HEIMEL is not

HEIMEL is not a model, agent framework, IAM replacement or generic policy engine.

Identity can establish who an actor is. A model can propose what to do. A workflow can route the work.

**HEIMEL decides whether it may become real.**

---

<p align="center"><strong>HEIMEL</strong><br>Intent. Realized.</p>
