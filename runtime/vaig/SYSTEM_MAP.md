# VALO System Map

Status: authoritative working map  
Date: 2026-08-02  
Scope: active architecture, terminology and IP boundary control

This file is the controlling map for the current VALO architecture. Historical collaboration material is preserved separately and is not a normative runtime dependency.

## 1. Core thesis

AI risk becomes operational when probabilistic output is permitted to change the world.

VALO governs the path from observation and proposed action to evaluation, clearance, enforcement and evidence.

```text
Reality
  ↓
Speider
  ↓
BARO
  ↓
MAL — model/runtime/output-contract admission
  ↓
VALO Harness / model and tool orchestration
  ↓
Model proposal + optional RichStateEnvelope
  ↓
VAIG evaluation
  ↓
REHT clearance
  ↓
RACS decision and constraint binding
  ↓
VALO Core enforcement
  ↓
Execution
  ↓
Receipt / Veritas custody and outcome linkage
```

## 2. Active layer map

| Layer | Owns | Does not own |
|---|---|---|
| Speider | source discovery, connectors, collection, normalization and provenance | analysis, policy or governance decisions |
| BARO | observation, correlation, drift, convergence and Reality Packages | admissibility, clearance or execution decisions |
| MAL | admission of the exact model artifact, provider, runtime profile, task, data class, consequence class and required output contract | evaluation of the produced state, action clearance or execution authority |
| VALO Harness | context assembly, governed model routing, tool exposure, workflow orchestration, checkpointing and trace generation | authority, admissibility or execution clearance |
| Model / agent | proposed action, analysis, alternatives and required intermediate representation | self-attestation, authority, clearance or direct consequence-bearing execution |
| VAIG | runtime governance evaluation, evidence sufficiency, state quality, uncertainty, calibration, boundary risk, tail risk and escalation signals | final authority, execution clearance or formal state enforcement |
| REHT | present action admissibility and scoped commit-time clearance under current authority, policy, evidence, context, state and consequence | model orchestration, transport schemas or side effects |
| RACS | action-envelope, evidence, authority, policy, state, decision, constraint and receipt contracts | independent evidence evaluation, authority creation or runtime execution |
| VALO Core | deterministic execution-state transitions, clearance validation, halt, refusal, degraded mode, reset and receipt-linked enforcement | semantic judgment, human-state sensing or organizational policy creation |
| VALO Platform | product integration, user experience, memory, enterprise connectors and operating model | replacing the bounded responsibilities of the layers above |
| Receipt / WORM | tamper-evident chain of custody and execution-time attestation | proof that a decision was wise, lawful or true |
| Veritas | preservation of receipt custody and linkage to later observed outcomes | evaluation, authorization, clearance, enforcement, truth creation or causal proof |

## 3. Clean responsibility distinction

```text
Speider collects.
BARO observes and correlates.
MAL admits the exact model, runtime and output contract.
The Harness orchestrates.
The model proposes.
VAIG evaluates runtime evidence, state and risk.
REHT determines present admissibility and clears or refuses the exact action.
RACS binds the decision and constraints.
VALO Core enforces bounded state transitions.
Receipts attest what occurred.
Veritas preserves custody and links later outcomes.
```

No component may silently absorb the responsibility of another.

## 4. Rich-state evaluation path

For history-dependent or consequence-sensitive workflows, a direct model answer may be insufficient.

The canonical optional evidence object is `RichStateEnvelopeV1`.

It preserves:

- permitted history scope and digest;
- represented state and state digest;
- representation and granularity level;
- source evidence and transformation lineage;
- proposed action and action digest;
- alternatives, uncertainty and known omissions;
- boundary conditions and tail-risk summary;
- out-of-distribution and reversibility status;
- required authoritative-correction reference.

Canonical distinctions:

```text
history
!= represented state
!= evidence
!= model proposal
!= VAIG evaluation
!= admissibility
!= REHT clearance
!= RACS binding
!= execution
!= outcome
```

A state digest proves identity and integrity of a representation. It does not prove truth, completeness or sufficiency.

VAIG evaluates the actual produced envelope. MAL only admits the model, runtime and output contract.

See `docs/architecture/rich-state-evaluation-contract.md`.

## 5. Representation and granularity rule

The same real-world action may be represented as:

```text
agent step
→ tool call
→ workflow transition
→ transaction
→ organisational decision
→ external consequence
```

Mandatory rule:

> Governance is representation- and granularity-invariant, while remaining context- and consequence-sensitive.

This means:

- splitting one high-risk action into many small calls cannot evade governance;
- summarisation cannot remove evidence that would change authority or consequence;
- moving between agent, workflow and transaction levels preserves semantic and digest linkage;
- granularity changes cannot reduce consequence classification;
- cumulative effects must be evaluated where separate calls create one consequential outcome.

## 6. Governance object

The primary governance object is a proposed consequence-bearing action in its current state and context.

The governing question is not only:

```text
Who is authenticated and technically permitted?
```

It is:

```text
Is this exact action presently admissible under current evidence,
state, policy, authority and consequence — and may it be cleared now?
```

## 7. Active invariants

- No model is invoked outside a required MAL admission profile.
- No direct scalar output bypasses a mandatory rich-state output contract.
- No action crosses the execution boundary without REHT clearance and RACS binding.
- No stale or invalid authority silently persists into execution.
- Material changes in evidence, policy, context, state, representation or granularity require re-evaluation.
- A state digest proves identity, not truth or sufficiency.
- VAIG evaluation cannot create authority or clearance.
- Model self-review is not independent authoritative correction.
- Uncertainty, tail risk or boundary risk above the permitted threshold must escalate, defer, deny or halt.
- Enforcement state transitions remain deterministic and auditable.
- Every execution-relevant decision is linked to a receipt.
- Execution-time attestations remain distinct from later observed outcomes.

## 8. Human and organizational authority

Human and organizational authority enter the active architecture as explicit external inputs with provenance, scope, validity and delegation limits.

The active architecture does not depend on MECHA, EFA or any collaborator-specific framework. Historical or external frameworks may be cited as research context but are not native runtime components unless an explicit, documented integration is later approved.

## 9. Historical collaboration boundary

The jointly authored MECHA publication is retained with dual attribution.

Its contribution boundary is documented separately:

- Charles R. Rupp: EFA semantics, MECHA tuple, HSRS, Empty Cockpit doctrine and associated manuscript material.
- Njål Gaute Solland: TLA+ specification, model checking, verification results and VALO infrastructure descriptions.

The formal model is therefore a Solland-owned contribution inside a jointly authored publication, as stated in the Zenodo paper DOI `10.5281/zenodo.20668225`.

Historical collaboration material must not be indexed as current VALO architecture.

## 10. Naming rules

Use these names consistently:

- VALO = overall platform and architecture
- Speider = collection and source-provenance layer
- BARO = observation and intelligence layer
- MAL = exact model, runtime and required output-contract admission
- VALO Harness = model/tool orchestration and context runtime
- RichStateEnvelope = optional decision-relevant state and evidence representation; never authority
- VAIG = runtime governance evaluation
- REHT = present admissibility and commit-time clearance
- RACS = canonical deterministic decision and exchange-contract layer
- VALO Core = deterministic execution-state enforcement
- Receipt = decision and execution evidence object
- Veritas = receipt custody and later outcome linkage
- WORM = tamper-evident append-only storage pattern
- RRP = refusal-resolution lifecycle where retained

Do not use ACS or VACS as the active standard path. Those names are historical or superseded. Use RACS.

## 11. Claim maturity

Every material claim must be classified as one of:

- `concept`
- `specified`
- `implemented`
- `tested`
- `formally_checked`
- `independently_validated`
- `externally_certified`
- `unresolved`

AI-generated repetition, model consensus or polished prose is not independent validation.

The rich-state mapping is currently `specified`, not runtime-implemented or empirically validated in VALO.

## 12. Public and private boundary

Public concept-level language may include execution governance, continuous admissibility, deterministic enforcement, rich-state evaluation, evidence receipts and model independence.

Keep security-sensitive implementation details, customer policy profiles, hard thresholds, attack surfaces, test fixtures and deployment secrets private.

## 13. Strategic ordering

1. Stabilize IP, provenance and architecture boundaries.
2. Separate Speider, BARO, MAL, VAIG, REHT, RACS and Core responsibilities cleanly.
3. Specify `RichStateEnvelopeV1` and VAIG evaluation contracts.
4. Bind state, action and clearance fingerprints through RACS and receipts.
5. Complete deterministic runtime and receipt evidence.
6. Integrate through VALO Platform and enterprise adapters.
7. Build product intelligence and enterprise pilots on top.

## 14. Working one-liner

VALO preserves decision-relevant state, evaluates it independently and prevents any AI-mediated action from becoming real merely because a model proposed it.
