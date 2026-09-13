# Build Order: Bland conversational operations pattern adoption

Status: implemented

Canonical base at claim: `df22457b50a70ecf343e1342298af80d11e4328a`

Branch: `feat/bland-conversational-operations-patterns`

Claim/owner: ChatGPT execution worker

## Decision

Adopt the strongest reusable operational patterns visible in Bland AI into existing Factory OS, governed behavior promotion, Learning Factory and ACE evidence loops.

Do not create a Bland layer, a voice-specific factory, a second evaluator or a second authorization system.

Bland itself remains an optional conversational runtime behind `nsolland/valo-gateway`. The patterns below are provider-neutral and useful even when Bland is not deployed.

## 1. Production trace becomes reproducible defect evidence

A production failure should enter the factory with its originating evidence rather than as a free-text bug report alone.

Normalize at minimum:

- originating runtime/provider;
- trace/call/session reference;
- exact behavior/pathway/agent version;
- relevant tool and event-log references;
- observed outcome;
- expected outcome;
- reproduction inputs or safe fixture references;
- evidence digests.

Canonical loop:

```text
production observation
→ evidence-linked defect
→ deterministic/simulated reproduction
→ candidate patch
→ replay original failure
→ regression suite
→ independent QC
→ governed promotion
```

Sensitive production data must be represented by governed references or redacted fixtures where required.

## 2. Historical failures become permanent regression fixtures

Bland supports scenario testing, node-level testing and historical-call back-testing. Adopt the underlying rule:

```text
real failure once
→ regression fixture forever, while materially applicable
```

Fixtures may cover:

- ordinary success paths;
- edge cases;
- adversarial or confused users;
- interruptions;
- authentication failures;
- escalation/handoff;
- tool failures and stale data;
- policy/guardrail situations;
- channel-specific behavior;
- previously observed production failures.

A passing test is evaluation evidence. It is never activation authority.

## 3. Candidate/version/release separation

Editable behavior must not be confused with the version running in production.

Adopt the general state split:

```text
draft/candidate
→ stable digest/version
→ evaluation
→ release candidate
→ shadow/canary
→ active
```

Every evaluation, rollout and rollback must bind the exact artifact digest/version it applies to.

This reinforces `docs/architecture/governed-behavior-promotion.md`; it does not replace it.

## 4. Canary and rollback are general Factory primitives

Bland exposes staged real-traffic releases and rollback. Factory OS already has the stronger canonical lifecycle:

```text
REQUESTED
→ AUTHORIZED
→ SHADOW
→ CANARY
→ ACTIVE
→ QUARANTINED | ROLLED_BACK | RETIRED
```

Adopt Bland as external validation of this operating pattern.

Factory-specific invariants remain:

- provider Promote/Deploy controls are not authority;
- canary scope cannot silently widen;
- activation is receipt-bound;
- rollback restores an exact compatible previously validated version;
- Class C behavior cannot auto-activate;
- runtime consequential actions still require fresh REHT authorization after behavior activation.

## 5. Evidence-linked diagnose/fix/replay loop

Bland Triage and Norm demonstrate a useful operational loop where production evidence is attached to an issue, an agent diagnoses it, produces a patch and reruns simulations.

Adopt this workflow shape with VALO separation of duties:

```text
observed defect
→ evidence-linked issue
→ Discovery diagnoses
→ Execution/Writer proposes fix
→ replay original failure
→ regression suite
→ Judgment/Reviewer independently evaluates
→ promotion candidate
```

Critical rule:

```text
generator verification ≠ independent verification
```

The worker that creates the fix may run tests and provide evidence, but cannot be the sole attestor of correctness or promotion readiness.

## 6. Outcome labels feed Learning Factory, not authority

Conversational runtimes can classify operational outcomes such as resolved, transferred, booked, abandoned or failed.

Adopt a provider-neutral `outcome_ref` concept as an input to:

- Learning Factory;
- trajectory/outcome evaluation;
- regression discovery;
- ACE economic observability;
- operational quality dashboards.

Do not promote a provider outcome label directly to verified ROI. Economic claims require independent business-outcome evidence under the existing ACE economics contract.

## 7. Persistent memory is governed context

Cross-session memory is useful for continuity but dangerous if treated as mandate or permission.

Canonical Factory/Runtime rule:

```text
memory may influence context and proposals
memory cannot grant, widen, persist or revive authority
```

Memory artifacts should carry provenance, freshness, retention/revocation state and appropriate privacy handling. A resumed conversation or remembered customer preference cannot revive an expired execution permit.

## 8. One governed agent identity, many channel projections

Bland shares agent concepts across voice and messaging surfaces. Adopt this as a provider-neutral projection pattern:

```text
governed agent/workflow identity
→ voice adapter
→ SMS/message adapter
→ web/chat adapter
→ other channel adapters
```

Each channel action still binds its exact target, payload, context and consequence. Adding a new channel never widens the agent's mandate automatically.

## 9. Relationship to AI Work OS

AI Work OS is a first-class Factory OS target. Bland's operational patterns apply directly to Work OS capabilities produced by the factory.

Example:

```text
Work OS customer-service capability
→ Factory-built behavior/function/adapter
→ scenario + historical regression suite
→ independent QC
→ versioned artifact
→ governed promotion
→ Operator/runtime projection
→ voice/message provider such as Bland
→ exact consequence request
→ REHT
→ gateway
→ external system
→ Veritas/outcome evidence
→ Learning Factory
```

This creates a closed production-learning loop without allowing runtime observations or provider agents to self-modify active behavior.

## 10. External production proof opportunity

Bland is a useful optional reference runtime for proving that the VALO boundary is vendor-neutral.

A production proof can demonstrate:

```text
Bland conversation chooses refund_customer(...)
→ valo-gateway receives exact proposal + conversational context
→ VAIG evidence
→ REHT permits or denies exact refund
→ one-shot permit consumed
→ payment adapter executes only on valid clearance
→ Veritas records result
```

The same REHT/gateway contracts must remain unchanged when Bland is replaced by another conversational runtime. Only provider adapter/configuration may change.

## Machine-readable adoption

`config/ecosystem-adoptions.json` now registers `bland-conversational-operations` with `authority_effect=none`.

`tests/test_ecosystem_adoptions.py` gates the critical properties:

- production failures become regression fixtures;
- provider test pass is evidence, not activation;
- fixing worker cannot self-attest success;
- independent QC remains mandatory;
- memory is context, not mandate;
- memory cannot revive authority;
- channel projection cannot widen authority.

## Do not adopt

Do not adopt any interpretation where:

- Bland becomes a canonical architecture layer;
- voice becomes a special authority path;
- guardrail pass means execution clearance;
- caller authentication means business authorization;
- a provider test/eval can activate behavior;
- Norm or another fixing agent self-attests its own patch;
- a canary release silently expands scope;
- provider memory contains durable authority;
- an outcome tag proves business value;
- a provider credential creates mandate;
- a provider-specific schema leaks into REHT or RACS.

## Sources reviewed

- https://www.bland.ai/
- https://www.bland.ai/product
- https://www.bland.ai/changelog
- https://www.bland.ai/glossary
- https://www.bland.ai/pricing

## Canonical invariant

```text
Provider runtimes converse and propose.
Factory OS learns, builds, tests and promotes artifacts.
VAIG evaluates.
REHT authorizes exact consequential execution.
Gateway enforces the cleared action.
Veritas records what actually happened.
Learning Factory turns verified outcomes back into new evidence and build work.
```
