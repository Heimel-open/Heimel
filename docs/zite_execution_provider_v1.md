# Zite as a Governed Execution Provider v1

Status: adopted integration pattern
Date: 2026-09-04

## Purpose

Zite is treated as an optional external execution provider: a surface through which an already-governed VALO action may cause business effects in Zite itself or in downstream systems reached through Zite workflows and integrations.

Zite is not an authority source, policy engine, Kernel dependency, or source of authoritative truth.

## Canonical boundary

```text
worker / agent
  -> governed workspace
  -> exact-action conformance
  -> VAIG evaluation
  -> REHT fresh authority resolution
  -> RACS ALLOW | DENY | ESCALATE
  -> bounded execution grant
  -> Gateway provider adapter
  -> Zite MCP / workflow
  -> Zite / downstream business effect
  -> run/webhook/provider evidence
  -> Veritas verification
  -> BARO postcondition/divergence check
  -> Kernel event
```

The provider adapter MUST NOT expose a direct route from a worker, MCP client, workflow author, model, or Zite credential to an external consequence.

## Core semantic separation

The integration preserves four distinct concepts:

```text
technical permission != approval != authority != right-to-act-now
```

A Zite OAuth session, database permission, workflow permission, integration credential, or prior human approval establishes at most technical capability or prior approval. None establishes current VALO authority.

Fresh REHT resolution at consequence time remains mandatory.

## Execution grant requirements

Before a Zite consequence may be invoked, Gateway MUST receive one valid bounded execution grant that binds at minimum:

- tenant/principal
- actor identity
- purpose
- exact operation class
- exact target/resource identity where known
- relevant arguments or canonical argument digest
- current authority/delegation basis
- governing state root
- constraints and limits
- issued-at and expiry
- idempotency key
- execution/provider route identifier

The grant MUST fail closed on expiry, tampering, route mismatch, target mismatch, argument commitment mismatch, stale authority, revoked delegation, or changed governing state where freshness is required.

A provider token MUST never substitute for this grant.

## Zite adapter responsibilities

The Zite adapter is responsible only for translating an already-authorized effect into the provider call and returning provider evidence.

It MUST:

1. accept only bounded Gateway calls derived from an active execution grant;
2. map the exact authorized action to one specific Zite MCP operation or workflow invocation;
3. propagate the VALO correlation/idempotency identifier when the provider surface permits it;
4. reject any request that would widen the authorized action;
5. record the Zite workflow/run identifier or equivalent provider receipt;
6. capture provider response metadata without elevating it to authoritative truth;
7. return enough evidence for Veritas to verify the expected effect independently where possible.

It MUST NOT:

- infer missing authority from Zite permissions;
- widen action scope because the connected Zite account can do more;
- reuse an execution grant for a materially different action;
- treat workflow success as proof that the intended real-world effect occurred;
- write authoritative Kernel state directly.

## Evidence correlation

Zite workflow/run logs and signed webhook events may be useful evidence sources. They are provider-originated observations, not self-authenticating truth.

The preferred evidence chain is:

```text
VALO execution-grant id
  <-> Gateway invocation id
  <-> Zite workflow/run id
  <-> provider response / webhook event id
  <-> observed downstream state/effect
  <-> Veritas receipt
```

Where Zite provides webhook signatures, timestamps, before/after records, event IDs, or origin metadata, Veritas SHOULD preserve and verify them. A valid provider signature proves provider-originated bytes; it does not by itself prove semantic correctness, authority, completeness, or downstream finality.

## Replay and idempotency

Zite workflow replay is useful for diagnosis but MUST NOT be treated as authorization replay.

A replay that can create a new consequence requires a new fresh REHT decision unless it is provably the same idempotent effect under the same still-valid bounded grant and provider semantics.

Provider retries MUST preserve the original idempotency key and MUST NOT create duplicate business effects.

## Revocation race

The critical demonstrator is the gap between approval/permission and current authority.

Example:

```text
09:00 human approves workflow action
09:03 authority or limit is revoked/changed
09:05 worker attempts the approved Zite effect
09:05 REHT resolves current authority
      -> DENY or ESCALATE
      -> no Zite invocation
```

This is the required behavior even when the Zite account, OAuth token, database permission, or workflow permission remains technically valid.

## Downstream integrations

A Zite workflow may itself call another external system. Such composition does not weaken the governed boundary.

The authorized consequence must describe the materially intended downstream effect, not merely `run workflow X`, whenever the workflow can create business consequences beyond Zite.

A workflow definition change that can alter the consequence behind the same invocation identifier is decision-relevant configuration and MUST be treated as drift. The bound workflow/version/digest must be checked where provider capabilities permit it; otherwise the route is lower-assurance and must be classified accordingly.

## Capability routing

Zite may be registered as one provider behind a capability route, for example:

```text
capability: create_customer_case
providers:
  - native-demo
  - zite-workflow
  - direct-servicenow
```

Provider selection does not move authority out of VALO. The same semantic action contract and authorization requirements apply across routes.

## Sovereignty and replaceability

Zite remains replaceable. Loss of Zite may remove an execution route but must not remove VALO identity, authoritative state, rights, delegation, policy, evidence history, or recovery capability.

No native Kernel or conformance test may require Zite availability.

## Conformance expectations

A Zite provider implementation is conformant only if negative tests prove at least:

- no direct worker-to-Zite effect path;
- expired grant -> no provider call;
- revoked authority after approval -> no provider call;
- target/argument mismatch -> no provider call;
- broader Zite permission does not widen the action;
- replay cannot bypass fresh authorization;
- duplicate retry does not duplicate the effect;
- provider success without verified effect is not treated as verified success;
- signed webhook with wrong correlation cannot satisfy the expected effect;
- downstream workflow drift is detected or explicitly classified as lower assurance.

## Adoption decision

Adopt Zite as an optional governed execution provider and demonstrator.

Do not reproduce Zite's database/workflow/integration platform inside VALO. Use it to demonstrate the missing control boundary: technical capability and approval are insufficient; consequence-bearing action requires current right-to-act-now and verifiable effect evidence.
