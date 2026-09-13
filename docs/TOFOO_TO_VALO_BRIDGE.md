# Tofoo → VALO Bridge

**Purpose:** make the relationship between Tofoo, Φ-loven, LIM, VAIG, VALO L1, Janus/WORM and ACS explicit.

This document prevents future assistants from treating Tofoo as unrelated narrative material or treating VAIG as a mere guardrail product.

---

## Core Thesis

Tofoo provides the language and ontology.

Φ-loven / LIM provides the principle.

VAIG provides the runtime admissibility layer.

VALO L1 Guardian provides deterministic enforcement.

Janus / WORM provides evidence.

ACS provides the standardization path.

In short:

```text
Tofoo = meaning
LIM = law/principle
VAIG = implementation
VALO L1 = enforcement
Janus/WORM = proof
ACS = protocol/standard
```

---

## The central mapping

| Tofoo / LIM concept | VALO / VAIG implementation | Meaning |
|---|---|---|
| Φ-filter | VAIG Core | shared filtering/admissibility engine |
| LIM | admissibility architecture | identity maintenance through structured filtering |
| Lovgiveren | TLA+ / VALO L1 Guardian | invariant rule layer that must not drift |
| Tolken | LLM / agent / model | adaptive interpreter that may evolve |
| Janus Sentinel | WORM audit log | append-only evidence layer |
| HALT | L4 / LOCK / L1 HALT | non-overridable stop condition |
| τ-window | coherence/admissibility bounds | allowed operational range |
| Friction | FRICTION / review cost | productive resistance before action |
| The next sentence | human decision / operator agency | the irreducible human commitment |
| Tofoo | mythic-symbolic carrier | the name that carries the cultural layer |

---

## Guardrail vs admissibility layer

Do not describe VAIG primarily as a guardrail.

A guardrail usually reacts to bad output.

An admissibility layer decides whether action is allowed before damage occurs.

Canonical wording:

```text
VAIG is the admissibility layer for AI systems.
It implements the Law of Identity Maintenance:
systems that cannot filter before action cannot preserve identity over time.
```

---

## Product interpretation

VAIG/VALO should be positioned as:

```text
an externally verifiable admissibility layer for AI execution
```

not merely:

```text
AI safety middleware
AI guardrail
LLM filter
policy wrapper
```

Those are partial descriptions only.

---

## Architecture interpretation

The Tofoo architecture distinction is:

```text
Lovgiveren must remain invariant.
Tolken must remain adaptive.
```

In VALO terms:

```text
L1 Guardian / formal spec = invariant Lovgiver
MCP / Sidecar / Proxy adapters = adaptive Tolker around runtime surfaces
VAIG Core = shared admissibility engine
Janus/WORM = irreversible memory of decisions
```

Do not let adapters become new Lovgivere. They must call the shared core.

---

## Human-facing protocol

Bok 3 contains the strongest operator/developer oath:

```text
Jeg bygger ikke systemer som drifter uten å dokumentere hvordan de holdes.
```

Recommended English form:

```text
I do not build systems that drift without proving how they are held.
```

This should be treated as a VALO builder principle, not just a literary line.

---

## Claim hygiene

Keep these layers distinct:

| Layer | Function | Risk if confused |
|---|---|---|
| Tofoo | myth / symbol / cultural carrier | may look unserious if used as empirical proof |
| Φ-loven | theory / hypothesis / synthesis | may be overclaimed if called proven everywhere |
| LIM | architectural principle | strongest bridge between theory and implementation |
| VAIG | runtime implementation | loses meaning if described as only middleware |
| VALO L1 | deterministic enforcement | loses guarantee if mixed with adaptive code |
| Janus/WORM | evidence layer | loses audit force if schemas drift |
| ACS | standard path | loses adoption if too idiosyncratic |

Rule:

```text
Never present symbolic truth, formal proof, simulation and empirical replication as the same kind of truth.
```

---

## Maturity labels for claims

Use these labels when writing papers, README files or external claims:

| Label | Meaning |
|---|---|
| M0 Symbolic | mythic, narrative or cultural claim |
| M1 Conceptual | architectural or philosophical claim |
| M2 Formal | mathematically or formally specified |
| M3 Simulated | tested in controlled simulation/toy environment |
| M4 Empirical | tested on real-world data or system runs |
| M5 Replicated | independently reproduced |
| M6 Standardized | adopted into protocol/standard/practice |

This does not weaken the idea. It protects it.

---

## What future assistants must not do

Do not:

- dismiss Tofoo as unrelated prose;
- rewrite Tofoo into generic AI-safety language;
- remove the Lovgiver/Tolk distinction;
- reduce VAIG to a guardrail;
- merge symbolic, formal and empirical claims into one proof category;
- rename Tofoo/LIM/VAIG/VALO concepts without human approval;
- edit Tofoo narrative material as if it were ordinary documentation.

---

## What future assistants should do

Do:

- preserve Tofoo as the cultural/ontological layer;
- use LIM as the bridge into architecture;
- use VAIG as the runtime implementation;
- use VALO L1 as deterministic enforcement;
- use Janus/WORM as evidence;
- use ACS as protocol/standardization path;
- mark claim maturity clearly;
- keep the human decision layer explicit.

---

## Operational bridge into current repo cleanup

This affects the current cleanup plan:

1. Extract VAIG Core from duplicated adapter logic.
2. Preserve HTTP Proxy, Sidecar and MCP as deployment modes.
3. Keep VALO L1 Guardian isolated as invariant Lovgiver.
4. Standardize WORM/audit receipt as Janus evidence.
5. Use `CLEAR -> WATCH -> FRICTION -> COUNCIL -> LOCK` as UI semantics.
6. Preserve Tofoo/LIM language in top-level positioning.

---

## One-line summary

```text
Tofoo gives VALO meaning; VALO gives Tofoo proof-of-work.
```
