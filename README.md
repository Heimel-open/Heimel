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

The minimum consequence path contains only the properties that cannot be removed:

```text
Kernel operative state + exact proposed effect
→ REHT fresh authorization
→ Gateway mechanical enforcement
→ external effect
→ Veritas proof
→ Kernel state admission
```

RACS is the deterministic contract binding the decision, exact effect, permit and receipt across REHT, Gateway and Veritas. It is not an active runtime hop.

| Component | Role |
|---|---|
| **Kernel** | Owns admitted operative state, deterministic replay and state admission; it does not authorize or execute |
| **REHT** | Authorizes or refuses the exact effect against fresh operative state |
| **RACS** | Binds decision, effect, permit and receipt as a deterministic contract |
| **Gateway** | Validates and consumes the one-shot permit on the only governed effect path |
| **Veritas** | Preserves attributable effect and outcome evidence for later state admission |

Workflow ISA and Function Fabric are conditional process/capability layers. VAIG is a conditional evaluator. None creates execution authority.

[Read the architecture →](docs/ARCHITECTURE.md)

## Open standards and infrastructure

The standards and reference contracts are open and vendor-neutral. Models, agents, workflows and applications can change without moving the consequence boundary.

HEIMEL now publishes three curated Apache-2.0 reference packages while canonical runtime ownership remains in the source repositories:

- **[Kernel reference core](packages/kernel)** — operative state, admission and deterministic replay
- **[Workflow ISA](packages/workflow-isa)** — typed deterministic process semantics
- **[Function Fabric](packages/function-fabric)** — provider-neutral governed Function composition
- **[REHT Standard](https://github.com/nsolland/reht-standard)** — fresh authority at consequence time
- **[RACS](https://github.com/nsolland/Racs)** — deterministic decision/action binding
- **[VALO Gateway](https://github.com/nsolland/valo-gateway)** — current public reference enforcement infrastructure; moving toward HEIMEL Gateway
- **[Veritas](https://github.com/nsolland/Veritas)** — verifiable consequence evidence
- **[Open Agent Contract](https://github.com/nsolland/open-agent-contract)** — portable governed action contracts

Adjacent public work remains separate from the HEIMEL runtime chain:

- **[PEACE Protocol](https://github.com/nsolland/peace-protocol)** — keeps authority and authoritative state in the governed domain while models, agents, devices and providers remain replaceable
- **[ACE economics](https://github.com/nsolland/opensource/blob/main/reports/01-the-ace-economy.md)** — measures scarce human evaluation and authority attention around governed completion; ACE is an economic model, not a protocol or source of authority

Current public layout:

```text
Heimel-open/Heimel
└── packages/
    ├── kernel
    ├── workflow-isa
    ├── function-fabric
    ├── mal
    ├── c-mcp
    ├── vaig
    ├── conformance
    ├── public-procurement
    └── sdk
```

The remaining public-release track covers VAIG and MAL clean-room reference surfaces, SDK/CLI/verifier tooling, integration surfaces and selected domain packs. The three reference-package tags are now published; registry artifacts and a coherent public end-to-end installation path remain open gates. Private production control-plane code is not implied by this roadmap.

## Design principles

**No direct effect path · Fresh authority · Exact action binding · Fail closed · Evidence by construction · Model independence**

## Verify the public packages locally

The repository includes a fail-closed release verifier. It builds every package,
runs the package test suites, checks wheel and source-distribution metadata,
installs the wheels in the declared publish order, and runs import smoke tests.
It never publishes and does not grant publication authority.

```bash
python3 tools/release_verify.py
```

The public contract SDK also includes an offline end-to-end demonstration:

```bash
valo-contracts demo
```

The measured receipt is written to `release-receipt.json` and the build outputs
to `dist/`; both are intentionally ignored by git. Use
[`release.yaml`](release.yaml) as the source of truth for package versions,
tags and release gates.

## What HEIMEL is not

HEIMEL is not a model, agent framework, IAM replacement or generic policy engine.

Identity can establish who an actor is. A model can propose what to do. A workflow can route the work.

**HEIMEL keeps the transition from intent to consequence bound to current authority, exact effect, exclusive enforcement and verifiable outcome.**

---

<p align="center"><strong>HEIMEL</strong><br>Intent. Realized.</p>
