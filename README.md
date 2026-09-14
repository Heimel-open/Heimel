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

HEIMEL sits immediately before effect and answers one question:

> **Does this intent have authority to become real — now?**

The first-level model does not depend on a model vendor, agent framework, workflow engine or enterprise system.

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

Enterprise exists for organization-level control: identity federation, SSO/SCIM, IAM integration, authority administration, separation of duties, approval flows, policy lifecycle, versioning and rollback, organization boundaries, delegated administration, multi-tenant isolation, secrets, deployment governance, HA/DR, retention, immutable evidence operations, observability, SLA and support.

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

HEIMEL governs the transition:

```text
intention → authorized consequence
```

## Design principles

**No direct effect path · Fresh authority · Exact action binding · Fail closed · Evidence by construction · Model independence · No mandatory phone-home**

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

Identity can establish who an actor is. A model can propose what to do. A workflow can route the work.

**HEIMEL keeps the transition from intent to consequence bound to current authority, exact effect, exclusive enforcement and verifiable outcome.**

---

<p align="center"><strong>HEIMEL</strong><br>Intent. Realized.</p>
