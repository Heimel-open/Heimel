# Execution Assurance Pilot — Integration Checklist

Use this checklist for one customer workflow. A checked box is evidence-backed; it is not inferred from intent.

## 1. Commercial boundary

- [ ] Customer and workflow owner are named.
- [ ] Exactly one tenant/environment is in scope.
- [ ] Exactly one workflow is in scope.
- [ ] Exactly one subject/agent class is in scope.
- [ ] Exactly one consequence-bearing action class is in scope.
- [ ] Customer states the decision/outcome question the pilot must answer.
- [ ] Out-of-scope systems/actions are recorded.

## 2. Effect boundary

- [ ] Existing final effect boundary is identified.
- [ ] Candidate action can be observed immediately before that boundary.
- [ ] SHADOW observer cannot block, mutate, retry, redirect or execute the action.
- [ ] Observer removal leaves customer execution unchanged.
- [ ] No alternate direct effect path is introduced by the pilot.

## 3. Identity and authority evidence

- [ ] Actor/subject identity source is identified.
- [ ] Authority/role/delegation source is identified.
- [ ] Purpose/mandate source is identified.
- [ ] Freshness semantics are defined for each authority fact.
- [ ] Revocation/change can be represented as changed evidence rather than cached permission.
- [ ] Missing authority evidence maps to unknown/insufficient evidence, not permission.

## 4. Action and world/resource state

- [ ] Exact action contract is defined.
- [ ] Target resource/object is stable and identifiable.
- [ ] Relevant before-state is available.
- [ ] Constraints/policy inputs are versioned or otherwise identifiable.
- [ ] Material state changes between observation and any later enforcement can be detected/revalidated.

## 5. Correlation

- [ ] `tenant_id` exists.
- [ ] `task_id` exists.
- [ ] `action_id` exists and is deterministic/stable for the observed candidate.
- [ ] Human/system decision can be joined back to `action_id`.
- [ ] Later effect/outcome receipt can be joined when available.
- [ ] Correlation collisions/duplicates have a deterministic handling rule.

## 6. Shadow operation

- [ ] Initial deployment mode is SHADOW.
- [ ] Shadow evaluation is non-authoritative.
- [ ] Shadow can issue no clearance/permit.
- [ ] Shadow performs no external effect.
- [ ] Tenant-scoped reads are enforced.
- [ ] Policy replay cannot alter customer execution.
- [ ] Human/system outcome comparison is append-only evidence.

## 7. Metrics and evidence quality

- [ ] In-scope action denominator can be measured independently of VALO where practical.
- [ ] Instrumentation gaps are counted.
- [ ] Evidence completeness is measured.
- [ ] Agreement/mismatch is measured.
- [ ] Escalation miss/false escalation is measured.
- [ ] Unknown/insufficient-evidence rate is measured.
- [ ] Decision latency is measured.
- [ ] Shadow external-effect count is monitored and must remain zero.
- [ ] Uncorrelated records are counted.

## 8. Runtime packaging

- [ ] Shadow runtime is pinned to exact immutable artifact/source SHA.
- [ ] REHT is pinned to exact immutable artifact/source SHA if included.
- [ ] RACS is pinned to exact immutable artifact/source SHA if included.
- [ ] Gateway is pinned to exact immutable artifact/source SHA if included.
- [ ] Veritas is pinned to exact immutable artifact/source SHA if included.
- [ ] VAIG is pinned if included.
- [ ] Image digests/SBOM/signatures follow normal `valo-distribution` release gates.
- [ ] Customer secrets remain in the approved external secret mechanism.

## 9. Promotion beyond shadow

Do not fill this section merely because the pilot is successful.

- [ ] Customer explicitly wants a move beyond SHADOW.
- [ ] SHADOW → RECOMMEND is a separate state change.
- [ ] RECOMMEND → ENFORCE is a separate state change; no skip.
- [ ] `ModePromotionCase` references real evaluation evidence.
- [ ] Owner and approver are different where separation of duties applies.
- [ ] Mandate reference is current.
- [ ] Rollback plan is executable.
- [ ] Rollback trigger is explicit.
- [ ] Validity/expiry is explicit.
- [ ] Promotion receipt is recorded.
- [ ] Exact action/state/authority is revalidated at the consequence-bearing instant.

## 10. Exit

Pilot may exit as any of:

- **STOP** — no sufficient value/evidence; remove observer.
- **CONTINUE_SHADOW** — useful but insufficient evidence for promotion.
- **RECOMMEND_ONLY** — recommendations are useful; customer retains execution decision.
- **PREPARE_ENFORCE_CASE** — evidence supports a separately governed promotion review.

There is no default progression to enforcement.
