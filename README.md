<p align="center">
  <img src="assets/brand/heimel-readme-hero.jpg" alt="HEIMEL — Intent. Realized." width="620">
</p>

<p align="center"><strong>Intent. Realized.</strong></p>

<p align="center">
<strong>Authority infrastructure for all consequential authority.</strong><br>
HEIMEL decides whether intent has the authority to become consequence — at the moment it matters — regardless of whether the actor is human, AI, software, workflow, API, robot or organization.
</p>

<p align="center">
<a href="https://reht.valoresearch.org/demos/executable-authority/"><strong>Run the demo</strong></a>
&nbsp; · &nbsp;
<a href="EVIDENCE.yaml">Evidence</a>
&nbsp; · &nbsp;
<a href="GOVERNANCE.yaml">Governance</a>
&nbsp; · &nbsp;
<a href="docs/open-enterprise-contract.yaml">Open / Enterprise</a>
</p>

---

## The boundary

```text
Intent → HEIMEL → Consequence → Evidence
```

Not every intent should become reality.

When humans can no longer keep a finger on every button, authority, boundaries and accountability must follow the button itself.

HEIMEL governs consequential authority, not a particular actor class. The actor may be a person, model, agent, workflow, enterprise system, API, robot or organization. What matters is whether that actor can create consequence.

HEIMEL sits immediately before effect and answers one question:

> **Does this intent have authority to become real — now?**

The first-level model does not depend on a model vendor, agent framework, workflow engine or enterprise system.

## Integration model

HEIMEL is designed to sit between existing enterprise control systems and the consequence-bearing executor rather than replace them.

```text
Identity / IAM / IdP
        ↓
Delegation + provenance
        ↓
Current authoritative state + policy inputs
        ↓
HEIMEL consequence-time authorization
        ↓
Bound permit
        ↓
Gated executor holding consequence capability
        ↓
Actual effect
        ↓
Verifiable effect evidence
```

Operational rules:

- **Identity is upstream input, not execution authority.** Existing IAM, IdP, SSO, workload identity and agent identity systems may establish who or what is acting. HEIMEL resolves whether that actor has current authority for the exact consequence.
- **Delegation attenuates.** Delegated authority cannot silently exceed the authority from which it was derived. Origin, scope, expiry, purpose and constraints remain attributable through the chain.
- **Policy engines are replaceable inputs.** Cedar, OPA, Cerbos-style PDPs or internal policy systems may contribute rules and context. They do not replace fresh authority resolution at consequence time.
- **Consequence capability belongs after the boundary.** Where possible, downstream credentials, signing capability, write access and other effect-bearing capability are held by the governed executor rather than the upstream actor.
- **No recorded authorization, no authorization.** An ALLOW must be bound to attributable evidence before execution authority is released.
- **Decision evidence and effect evidence are distinct.** HEIMEL must preserve what was authorized and what actually happened, so an authorization receipt cannot be mistaken for proof of external effect.
- **Replay precedes rollout.** Candidate authority or policy changes should be evaluated against recorded execution frames before activation when historical evidence is available.

## The clean-room model

HEIMEL can be understood as a governed clean room around consequence-bearing execution.

```text
WORLD
  ↓
DOOR       identity • provenance • admissibility • authority context
  ↓
UNIFORM    bounded role • workspace • capabilities • purpose
  ↓
SCRUB      reject or normalize unsafe, stale or untrusted state
  ↓
GATE       admit into governed workspace
  ↓
CLEAN HOUSE
           reasoning • planning • simulation • memory • collaboration
           internally free, while preserving:
           - NO_DIRECT_EFFECT_PATH
           - NO_IMPLICIT_CAPABILITY_TRANSFER
           - NO_UNGOVERNED_CROSS_WORKSPACE_PATH
  ↓
CHECK-OUT  exact proposed consequence
           → fresh authority
           → current constraints
           → exact effect binding
           → Gateway
           → real-world effect
           → Veritas
           → state admission / settlement
```

HEIMEL does **not** require approval of every internal thought, token, plan revision or simulation. Inside the governed workspace, reasoning can remain comparatively free.

The hard boundaries are admission, capability propagation, workspace relations and real-world consequence:

- **No hidden door out.** No API credential, database write, IAM grant, network route, service account, tool adapter or human administrative path may provide a real-world effect path outside Gateway.
- **No implicit transfer inside.** Communication does not transfer authority, tools, credentials, secrets or consequence-bearing capabilities. Capability-bearing transfer requires explicit authorization and a mediated path.
- **No ungoverned cross-workspace path.** Communication or state movement across workspace boundaries must remain mediated and attributable.
- **Check-out is always fresh.** Admission-time authority is not a reusable execution ticket. Every attempted real-world consequence is checked again against current authority and current constraints.

Canonical detail: [Heimel clean-room model →](docs/architecture/clean-room-model.md)

## Run it

### Executable Authority

**[Run the live authority demo →](https://reht.valoresearch.org/demos/executable-authority/)**

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

## Minimum consequence chain

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
| **Kernel** | Owns admitted operative state, deterministic replay and state admission |
| **REHT** | Authorizes or refuses the exact effect against fresh operative state |
| **RACS** | Binds decision, effect, permit and receipt |
| **Gateway** | Enforces the only governed effect path |
| **Veritas** | Preserves attributable effect and outcome evidence |

Workflow ISA and Function Fabric are conditional process/capability layers. VAIG is a conditional evaluator. None creates execution authority.

[Read the architecture →](docs/ARCHITECTURE.md)

## What can I deploy myself?

Open Heimel is intended to be independently runnable. A developer must be able to clone the repository, run the local governed consequence path, observe ALLOW / DENY, revoke authority, perform a fresh consequence-time check, replay the decision and inspect evidence without contacting Heimel.

The local reference runtime is under `runtime/runtime-local/`.

Run its contract and consequence-path tests with:

```bash
python -m pytest runtime/runtime-local/tests -q
```

Open Heimel has these hard guarantees:

- no phone-home requirement
- no license server
- no required Heimel cloud account
- no artificial disablement of local governed execution
- local authorization, enforcement, replay and evidence remain usable without a commercial entitlement

The repository contains the migrated runtime universe under `runtime/`, including Kernel, REHT, Gateway, Veritas, RACS, workflow/runtime components, adapters, packs, distribution and validation. `runtime/MIGRATION_MANIFEST.yaml` records source lineage.

## License and commercial boundary

The repository default is **Apache License 2.0** unless a component explicitly states otherwise.

Open Heimel may be used, modified, redistributed and operated commercially under Apache-2.0. The open mechanism is not crippleware and does not become chargeable merely because it is used in production.

Enterprise is a separate software/service and organizational-governance layer around the open mechanism. Commercial value must not depend on withholding the local governed-execution path behind a license server or mandatory vendor connection.

The Apache-2.0 license does not grant a right to represent an implementation as officially **Heimel Certified**. Official conformance/compatibility attestation remains a separate commercial act governed by Heimel's certification policy.

## Evidence and maturity

`EVIDENCE.yaml` is the bounded public evidence surface. It identifies measured test counts, critical negative cases, conformance evidence, release evidence and what is explicitly not established.

Current bounded statement: HEIMEL has executable local governed-execution, boundary and conformance evidence. Production-enterprise maturity must be assessed separately against deployment-specific evidence.

## Who controls HEIMEL?

`GOVERNANCE.yaml` defines current editorial/release authority, normative invariants, compatibility classes, change-control gates, conformance semantics and the boundary between open conformance and Heimel Certified.

A self-hosted Open Heimel deployment does not require Heimel or VALO Research as an online trusted party for local authorization, execution, replay or verification.

## Heimel Enterprise

Enterprise is separate governance infrastructure around the open governed-execution mechanism. It is not a license lock around local execution.

Enterprise exists for organization-level control: identity federation, SSO/SCIM, IAM integration, authority administration, separation of duties, approval flows, delegated administration, policy lifecycle, candidate-policy replay, shadow evaluation, versioning and rollback, organization boundaries, multi-tenant isolation, consequence-credential placement, secrets, deployment governance, HA/DR, retention, immutable evidence operations, observability, SLA and support.

```text
Heimel Open       → defines and implements governed execution
Heimel Enterprise → administers governed execution across an organization
Heimel Gateway    → sits on the consequence path
Veritas           → preserves attributable evidence
Heimel Certified  → provides official conformance / compatibility attestation
```

Managed deployment forms may include Heimel Cloud, Private Cloud, Sovereign and Air-gapped. These are deployment forms of the same governance semantics, not divergent products.

The canonical product boundary is machine-readable in `docs/open-enterprise-contract.yaml`.

## Pricing and settlement

The primary commercial unit is not a human seat and not an internal runtime tick.

```text
governed ticks → verified consequence → certification → settlement
```

**Meter internally by tick. Price and settle by verified consequence.**

Ticks may be used for observability, capacity, cost attribution, replay and audit. They are not the default customer billing object.

For Enterprise settlement, price and funding terms are bound before execution. A verified governed consequence may settle automatically against a prepaid balance, escrow or bounded payment allowance. Settlement is idempotent and at-most-once for the bound consequence.

By default:

- VERIFIED completed consequence → eligible for settlement
- DENY → no consequence charge
- ESCALATE → no consequence charge
- failed effect → no consequence charge
- unverified outcome → no consequence charge

A contract may define the price for a consequence class, but the protocol does not hard-code a universal dollar price.

Open Heimel remains free to run locally. Enterprise pricing applies to the separate organizational/commercial governance layer and its contracted settlement semantics.

> We do not charge to make governed execution possible. We charge to make governed execution governable at organizational scale.

## Heimel Certified

The conformance suite is open. Official certification is separate.

An official Heimel attestation must bind at least implementation identity, conformance-suite version, tested profile, result, issuance time and validity.

Passing the open conformance suite does not by itself imply official Heimel certification.

## Provider independence

HEIMEL does not depend on who forms intent. Models, agents, humans, workflows, enterprise systems, robots, IoT and payment systems can all sit upstream.

Identity, policy and orchestration remain replaceable inputs. Consequence-bearing capability remains downstream of the governed boundary wherever deployment architecture permits it.

HEIMEL governs the transition:

```text
intention → authorized consequence
```

## Design principles

**No direct effect path · No implicit capability transfer · No ungoverned cross-workspace path · Fresh authority · Delegation attenuation · Exact action binding · Consequence capability after the boundary · Fail closed · Evidence before allow · Decision/effect evidence separation · Replay before rollout · Model independence · No mandatory phone-home**

## Verify packages locally

```bash
python3 tools/release_verify.py
```

The contract SDK also includes an offline contract demonstration. It does not itself claim to execute the complete governed consequence path:

```bash
valo-contracts demo
```

Use `release.yaml` as the source of truth for package versions, tags and release gates.

## What HEIMEL is not

HEIMEL is not a model, agent framework, IAM replacement or generic policy engine.

Identity can establish who an actor is. A policy engine can express rules. A model can propose what to do. A workflow can route the work.

**HEIMEL keeps the transition from intent to consequence bound to current authority, exact effect, exclusive enforcement and verifiable outcome.**

---

<p align="center"><strong>HEIMEL</strong><br>Intent. Realized.</p>
