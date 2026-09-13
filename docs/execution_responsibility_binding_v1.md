# Execution Responsibility Binding v1

VALO already makes authority, delegation, purpose, state, authorization, disposition and effect evidence explicit. Execution Responsibility Binding makes one additional question first-class:

> Who carried which operational responsibility at the instant a consequence-bearing effect was allowed to commit?

This is not a legal-liability engine. It is deterministic evidence infrastructure for later responsibility and liability analysis.

## Canonical placement

```text
Authoritative sources
    -> Authority State / governed state resolution
    -> VAIG where smart evaluation is required
    -> REHT authorization
    -> RACS disposition
    -> Execution Responsibility Binding
    -> governed effect path / PEP
    -> external effect
    -> Effect Responsibility Evidence / Veritas
```

The pre-effect binding is sealed after the actual REHT decision and RACS disposition exist, but before the PEP is permitted to commit the external effect. This lets the binding reference the exact decision/disposition without creating a circular dependency.

The binding does not authorize, issue clearance, issue disposition or execute. REHT remains the authorization boundary, RACS remains the deterministic disposition contract and the PEP remains the enforcement boundary.

## Required responsibility roles

Every pre-effect binding names at least:

- `PRINCIPAL` — the principal on whose behalf the action is being performed
- `AUTHORITY_SOURCE` — the source that established the operative authority
- `STATE_PROVIDER` — one or more authoritative providers of state used by the decision path
- `AUTHORIZATION_EVALUATOR` — the component responsible for the commit-time authorization evaluation
- `DISPOSITION_ISSUER` — the component that issued the binding disposition
- `ENFORCEMENT_OWNER` — the component responsible for enforcing that disposition at the effect boundary
- `EXECUTION_PROVIDER` — the component that performs or settles the external effect

`POLICY_OWNER` is a core optional role because policy ownership may be material even when policy evaluation itself is upstream.

Domain packs may add namespaced roles such as `banking:SettlementSponsor`, but custom roles cannot substitute for the required core responsibilities.

Each assignment must include at least one explicit `basis_ref`. Optional obligation, contractual, regulatory and evidence references can bind the assignment to the source that makes the responsibility meaningful.

## Pre-effect contract

`ExecutionResponsibilityBinding` binds the exact:

- tenant
- action
- authority and delegations
- purpose
- Authority State reference and state root
- REHT decision reference
- RACS disposition reference
- clearance reference
- responsibility assignments
- binding time

The complete object is canonicalized and hashed as `binding_digest`. Any mutation changes the digest and validation fails closed if the stored digest does not match the content.

Fixed safety semantics:

- `legal_liability_determined = false`
- `authority_effect = NO_AUTHORITY_CREATION`
- `can_issue_clearance = false`
- `can_issue_disposition = false`

The contract therefore makes responsibility evidence explicit without claiming that VALO has determined legal liability.

## Post-effect evidence

After execution, `EffectResponsibilityEvidence` binds:

- the exact pre-effect `binding_digest`
- action, decision, disposition and clearance correlation
- the external `effect_ref`
- the effect/settlement `receipt_ref`
- verifier identity
- supporting evidence references
- observation time

This creates the evidence chain:

```text
Authority -> Decision -> Disposition -> Responsibility -> Effect -> Evidence
```

The post-effect object is separately canonicalized and hashed as `effect_binding_digest`.

A receipt that points at a different pre-effect responsibility digest is not equivalent evidence. A modified effect reference, decision reference or clearance reference invalidates the effect-responsibility digest.

## Liability boundary

Execution Responsibility Binding must never be presented as an automated allocation of legal liability.

Legal liability can depend on statute, payment rules, contract terms, negligence standards, outsourcing arrangements, jurisdiction and facts outside the execution contract.

VALO's narrower claim is stronger and testable:

> REHT does not determine legal liability. VALO makes the responsibility chain provable at the moment liability can arise.

This gives legal, operational-risk, insurance and audit functions a shared deterministic record of who supplied authority/state, who evaluated authorization, who issued the disposition, who enforced it and who executed the effect.

## Product positioning

Authorization answers:

> May this action proceed now?

Execution Responsibility Binding answers:

> Who carried each defined responsibility when it proceeded?

Effect Responsibility Evidence answers:

> Which real-world effect was produced under that exact responsibility binding?

Together they support responsibility allocation at execution time without changing the canonical VALO separation of concerns.
