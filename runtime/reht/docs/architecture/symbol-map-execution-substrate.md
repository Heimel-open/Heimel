# Symbol map — execution substrate and credential boundary

Date: 2026-08-23
Source: `nsolland/valo-platform` main

This map answers one question: what concrete safety semantics already existed beneath REHT/RACS/Gateway before `valo-reht::EffectBoundary` was introduced?

## ExecutionSubstrate contract

`execution_substrate/protocol.py::ExecutionSubstrate`
- `prepare(grant)`: create ephemeral isolated environment for an already-approved grant.
- `precommit_check(prepared, commit)`: final fail-closed revalidation immediately before irreversible commit.
- `execute(prepared, cleared_commit)`: controlled external effect.
- `collect_evidence(prepared)`: normalize substrate/security evidence.
- `revoke(prepared, reason)`: revoke grants on denial/mismatch/timeout/HALT.
- `terminate(prepared)`: deterministic teardown and credential revocation.
- Authority: none. Contract explicitly says legitimacy/necessity/authority/acceptable consequence remain REHT responsibilities.

`CommitLike`
- Exposes destination/method/path/action_hash/payload_hash/credential refs so credentials and effect can bind to the exact cleared commit rather than only a host or tool name.

## Core models

`NetworkDecision`: ALLOW/DENY egress result.

`PrecommitDecision`: PROCEED/DENY/HALT. This is a mechanical commit interlock, not REHT authorization.

`ExecutionStatus`: SUCCESS/FAILURE/REVOKED/TERMINATED.

`RollbackClass`: LOCAL_ROLLBACK/COMPENSATION/EXTERNALLY_IRREVERSIBLE.

`NetworkConstraint`
- exact host/method/path/port;
- wildcard only when explicitly allowed.

`ResourceCeiling`
- wall-clock, CPU, memory, storage, network byte, request count and max commit limits.

`CredentialGrantRef`
- opaque credential ref plus destination/operation/action/expiry and optional one-shot capability identity/digest.

`ExecutionConstraintSet`
- full network/destination/method/path/credential/resource envelope.

`ExecutionGrant`
- exact action/clearance/purpose/authority/payload/destination/method/path/credential/resource anchors;
- authorization-binding/commit/RACS/replay/validity/clearance/commitment digests;
- optional AAEC trajectory binding.
- Backward-compatible empty anchors may construct but fail closed at execute.

`ProposedCommit`
- still-reversible exact destination/method/path/action/payload/credential proposal.

`AuthorizationProof`
- wire representation of the authorization-bound commit envelope: authorization, clearance, RACS commit, action, mandate, context, commitment, evaluation, authority snapshot, replay, lifetime and optional AAEC trajectory.

`ClearedCommit`
- proposed commit plus verified authorization proof.

`PreparedExecution`
- ephemeral sandbox identity + exact grant/constraints/policy/substrate identity.

`ExecutionEvidence`
- normalized runtime/provider evidence bound to sandbox/substrate/policy/rule/network decision/request/destination/method/path/action/credentials/time/status/provider ref/result hash, plus optional trajectory lineage.

`ExecutionResult`
- terminal status + evidence + rollback class + deterministic result hash + provider ref.

## Default-deny policy compilation

`policy_compiler.py`
- compiles `ExecutionConstraintSet` to deterministic L7 policy;
- exact host/method/path/port;
- wildcard requires explicit approval;
- default decision DENY;
- resource ceilings carried into substrate provisioning;
- deterministic policy hash.

Semantic invariant: an executor cannot infer extra egress from a clearance; only explicitly compiled scope is reachable.

## Authorization proof / replay boundary

`authorization_proof.py::ReplayProtectionStore`
- atomic replay-consumption contract.

`SQLiteReplayProtectionStore`
- durable shared replay state; survives process restart and does not rely on Python object lifetime.

`verify_authorization_proof`
- validates canonical commit/proof schema and digests;
- exact action/clearance/commitment/authority/current commit/credential/timestamp bindings;
- rejects authority creation;
- validates optional trajectory binding;
- atomically consumes replay key before credentials/provider effect.

Current issue: this proof chain is still shaped around the old RACS authorization envelope. Mechanism is valuable; artifact binding is stale relative to the proposed two-authoritative-core model. Status: `PRESERVED_COMPONENT_STALE_BINDING`, not redundant.

## In-memory reference substrate

`in_memory.py::InMemoryExecutionSubstrate`
- same fail-closed interface as real adapters;
- prepare compiles policy;
- precommit checks exact commit bindings and expiry;
- execute verifies authorization proof before egress/credential/effect;
- audit channel must be live;
- default-deny policy applies;
- emits normalized evidence + deterministic receipt hash;
- revoke/terminate revoke credentials and live execution state.

This proves that the mechanical boundary existed independently of a specific sandbox provider.

## CubeSandbox adapter

`ShadowCubeSandboxClient`
- default-deny shadow backend for tests/pilots; no real external side effect.

`CubeSandboxExecutionSubstrate.prepare`
- rejects expired grant;
- compiles policy;
- creates sandbox;
- installs policy;
- unverified policy install terminates sandbox and fails closed.

`precommit_check`
- exact destination/method/path/action/payload/credential binding;
- expiry -> HALT;
- missing audit capability -> HALT.

`execute`
- verifies authorization proof at boundary;
- egress policy match required;
- credentials resolve only at verified outbound boundary;
- audit channel must be live before commit;
- emits normalized evidence + receipt hash.

`revoke` / `terminate`
- revoke all credential grants; deterministic teardown.

`_binding_mismatches`
- explicit commit-vs-grant check.

## QM sandbox adapter

`QMSandboxProfile`
- backend identity, persistence mode, process-session support, egress enforcement class, control-plane attestation, audit capability, deterministic teardown.

`QMSandboxPayloadResolver` / `InMemoryQMSandboxPayloadResolver`
- exact payload is retrieved by digest; re-hashed before release.

`QMSandboxClient`
- provider abstraction for provision/policy/run/process/audit/teardown.

`ShadowQMSandboxClient`
- no real external effect; can simulate timeout, dispatch, policy, audit, teardown and identity failures.

`QMSandboxExecutionSubstrate.prepare`
- grant freshness;
- payload digest resolution;
- sandbox reuse only when exact active handle/profile exists;
- observed backend profile must not drift;
- required feature support;
- deterministic policy install verification;
- failed install must terminate; unverifiable teardown escalates to HALT.

`_provision`
- resource ceilings become provider limits;
- incomplete handle/backend mismatch -> terminate + HALT.

`precommit_check`
- exact commit binding;
- freshness;
- active sandbox identity/profile;
- required domain egress enforcement;
- policy status/hash/default-deny/enforcement identity;
- audit channel live.

`execute`
- reruns precommit;
- policy match;
- payload bound to same sandbox;
- authorization proof verified/replay consumed;
- credentials resolved only after proof;
- dispatch; credentials cleared and revoked on all paths;
- failures terminate sandbox;
- response sandbox identity must match;
- audit persistence failure after effect marks state indeterminate and terminates;
- emits evidence + deterministic receipt.

`_dispatch`
- supports RUN and bounded process-session operations;
- process operation must equal cleared method;
- follow-up operations must target same sandbox;
- cross-sandbox follow-up denied.

`_terminate_after_failure` / `_terminate_handle_verified`
- failed action plus unverifiable teardown becomes HALT;
- termination/destroy/sandbox identity must all be verified before handle forgotten.

`encode_qm_provider_reference` / `decode_qm_provider_reference`
- typed sandbox/process/cursor continuation reference, strict version/shape.

## Capability-bound adapter lane

`adapters/capability_bound.py::_GrantBoundCapabilityBroker`
- holds current grant in `ContextVar` only for one execute call;
- credential release outside active grant -> revoke + fail.

`_CapabilityBoundSubstrateMixin`
- strict capability broker required at construction;
- rejects legacy/mixed/duplicate/incomplete credential refs;
- prepare/precommit/execute/revoke/terminate all revoke capability/secret state on failure or completion;
- inability to verify revocation becomes HALT.

`CapabilityQMSandboxExecutionSubstrate` / `CapabilityCubeSandboxExecutionSubstrate`
- provider adapters using strict one-shot credential lane.

## Runtime capability projection

`RuntimeCapabilityProjectionV1`
- non-secret one-shot projection bound to subject/tenant/purpose/action/payload/destination/operation/path/clearance/replay key/human approval/lifetime.

`StandingCapabilityGrantV1`
- standing human-approved scope may mint future projections but is never accepted at execution boundary.

`RuntimeCapabilityService.issue_standing_grant`
- human approval verified;
- exact scope/purpose/lifetime must be bound;
- standing grant cannot outlive human approval.

`project`
- current ExecutionGrant required;
- exact destination/operation/path;
- direct projection requires human approval or valid standing grant;
- projection lifetime is intersection of grant and authority approval.

`consume_for_boundary`
- state must be ACTIVE;
- signature/digest/credential/grant/commit/standing scope exact;
- consumes before secret lookup/provider dispatch;
- any retry requires a fresh projection.

`revoke_projection`, `revoke_for_refs`, `revoke_by_clearance`, `revoke_by_attestation`, `revoke_standing_grant`
- monotonic narrowing/revocation entry points.

## Credential brokers

`CredentialStore`
- secret backend only accessible at verified boundary.

`InMemoryCredentialStore`
- test/reference only.

`CredentialBroker`
- legacy path;
- production mode blocks unbound local bearer minting;
- capability-bound refs are rejected and must use strict broker;
- destination/operation/action binding checked before resolution;
- exact credential ref substitution denied.

`CapabilityBoundCredentialBroker`
- strict one-shot projection path;
- capability projection must match current grant and exact commit before secret release;
- capability consumed before secret resolution;
- revocation follows terminal paths.

## Credential-delivery PDP

`CredentialPolicyDecisionPoint.evaluate`
- secret-free deterministic policy decision beneath execution boundary;
- re-verifies signed RACS credential-delivery authorization;
- exact clearance/action/current authority/delegation/policy/context digests;
- tenant/principal/agent/workload/connector/audience/resource/operation binding;
- requested scope may only narrow;
- parameter constraints may not broaden;
- PoP method/key bound;
- requested lifetime cannot exceed authorization/clearance;
- renewable lease forbidden;
- bounded use required;
- revocation/audit/receipt infrastructure must be available;
- workload attestation mandatory;
- invalid signed authorization -> HALT; policy mismatch -> DENY; does not self-escalate to STEP_UP.

`Ed25519RACSAuthorizationVerifier`
- exact artifact digest + trusted signing key.

Legacy issue: credential authorization model allows clearance decision `ALLOW` or `MODIFY`, so it embeds the old wider RACS plane and must be remapped if REHT remains exactly ALLOW/STEP_UP/DENY.

## Credential-delivery CDP

`CredentialDeliveryPoint.deliver`
- CDP has no policy discretion;
- only trusted signed PDP ALLOW decision;
- decision is single-use;
- revocation and audit availability checked before provider delivery;
- provider returns only opaque token reference;
- bounded lease created;
- audit receipt must persist or lease/provider credential is terminated/revoked and delivery fails.

`activate_lease`
- moves ISSUED -> ACTIVE through registry.

`renew_lease`
- intentionally calls a registry operation that always fails; leases are non-renewable.

## Lease state machine

`LeaseRegistry`
- explicit ISSUED/ACTIVE/CONSUMED/EXPIRED/REVOKED/TERMINATED states;
- bounded use count;
- terminal state after exhaustion;
- renew always prohibited;
- refresh-token delivery always prohibited;
- effectiveness requires state, time and remaining use.

Semantic invariant: a delivered credential cannot silently become standing reusable authority.

## Proof of possession

`DPoPProof`
- key, method, URI, time, exact canonical request digest, optional token hash.

`ProofIdStore.consume_once`
- replay barrier.

`DPoPProofVerifier.verify`
- store availability fail-closed;
- confirmation-key binding;
- key thumbprint integrity/signature;
- proof-id single-use;
- method/URI/request digest/time/token hash exact.

Semantic invariant: copied bearer material is useless without the bound private key and exact request.

## Workload identity

`WorkloadAttestation`
- SPIFFE/SVID-style workload identity + ephemeral key + tenant/agent/workload/lifetime.

`SpiffeWorkloadIdentityVerifier.verify_bound`
- trusted signer;
- trust-domain/ID shape;
- confirmation-key binding;
- current lifetime;
- exact workload/tenant/agent binding.
- Explicitly proves workload identity only, never human/organizational authority.

## Revocation

`RevocationRegistry`
- separate blocking boundary; never mints/resolves credentials;
- unavailable registry -> fail closed;
- lease and authorization revocation checked independently;
- honest provider state: CONFIRMED / RESIDUAL_WINDOW / UNKNOWN.

Semantic invariant: boundary blocks even when provider-side revocation cannot be honestly confirmed; residual exposure is evidence, not hidden.

## Credential audit

`CredentialAuditSink`
- append-only, non-secret audit boundary.

`ReceiptPersister`
- availability prerequisite for issuance/use.

`CredentialAuditEvent`
- exact authorization/clearance/decision/lease/provider/scope/target/operation/PoP/reason correlation, never token value/private key.

`emit_lease_receipt_event`
- canonical lease receipt -> audit event.

## Cross-agent scope composition

`ScopeCompositionDetector.detect`
- groups active leases by agent;
- detects policy-declared prohibited effective scope combinations across collaborating agents/delegation tree;
- emits `CompositionEvidence` with `grants_deny=False`.
- Evidence goes to governance pipeline; it does not independently create DENY or authority.

## Provider boundary

`CredentialProvider`
- exclusive access to provider credential material/vault refs;
- deliver returns opaque `IssuedCredential`, never plaintext token;
- explicit revoke/status.

`ResidualValidityProvider`
- does not falsely claim immediate revocation; reports residual validity window.

`ProxyForwarder`
- fallback where narrow provider token cannot be minted;
- base credential remains inside proxy boundary;
- checks lease, revocation, PoP, exact target and bounded use;
- strips auth/cookie headers and non-approved headers;
- no open-forwarding mode;
- redirect policy is explicit allowlist.

## Comparison with `valo-reht::EffectBoundary`

`EffectBoundary` preserves:
- fresh context obtained within commit;
- REHT called for exact action snapshot;
- DENY/STEP_UP no effect;
- execution-context hash check;
- atomic single-use permit via injected store;
- consume before effect; failure does not re-arm.

It does not preserve by itself:
- prepare/isolation lifecycle;
- provider/substrate identity;
- default-deny L7 egress;
- exact destination/method/path/payload/credential commit model;
- durable authorization-envelope replay;
- resource ceiling enforcement;
- payload resolver/hash release;
- workload identity;
- one-shot capability projection;
- secret-release boundary;
- PoP;
- non-renewable bounded credential leases;
- credential/revocation/audit availability fail-closed;
- exact provider revocation truth/residual window;
- deterministic teardown and teardown verification;
- post-effect audit persistence/indeterminate-state handling;
- normalized substrate evidence/receipt;
- cross-agent scope-composition evidence.

Therefore the old execution substrate is not semantically redundant. The correct consolidation target, if two authoritative cores remain the goal, is likely:

`Kernel state -> REHT authorization -> subordinate ExecutionSubstrate commit boundary -> verified evidence/outcome -> Kernel`

The substrate remains non-authoritative. Removing its authority role is compatible with retaining its mechanics. Replacing it with a smaller generic callable boundary is not yet semantically equivalent.
