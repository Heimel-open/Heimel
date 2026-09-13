# Dependency Topology and Concentration Risk v1

## Principle

Redundancy must be evaluated across dependency and authority domains, not topology alone.

Two routes are not independent merely because they have different names, endpoints, providers, regions, models, workers, or physical paths. If they share a consequence-bearing dependency or controller, that shared point can become transit power over governed execution.

Canonical invariant:

> No single dependency should silently become transit power over governed execution.

## Governed dependency domains

The v1 contract makes seven domains explicit:

- `PHYSICAL_PATH`
- `PROVIDER`
- `JURISDICTION`
- `AUTHORITY_SOURCE`
- `CREDENTIAL_CONTROL_PLANE`
- `EXECUTION_PEP`
- `RECOVERY_PATH`

A route may carry more than one dependency in a domain. A domain is only eligible for an independence conclusion when the route explicitly declares that domain complete and every referenced dependency is sealed, `VERIFIED`, and fresh at evaluation time.

## Deterministic outcomes

`assess_dependency_diversity` produces one of three non-authorizing results:

- `INDEPENDENT`: at least two routes, complete fresh evidence in every required domain, and no shared dependency or shared controller across routes.
- `CONCENTRATED`: complete fresh evidence exists, but at least one dependency or controller is shared by multiple routes.
- `INDETERMINATE`: independence cannot be proven because routes are insufficient or required dependency evidence is incomplete, stale, unknown, conflicted, revoked, or otherwise not verified.

Unknown is never treated as independent.

The report also records deterministic concentration findings and `max_concentration_bps`, the largest share of evaluated routes controlled by one known dependency or controller.

## Boundary semantics

Dependency diversity creates no authority and cannot issue execution clearance. It is deterministic governed state/evidence that can be consumed by risk evaluation, policy, VAIG, or REHT without moving the authorization boundary into the Kernel.

The execution chain remains:

`Kernel state/projection -> worker -> conformance -> fresh authority/state -> REHT -> RACS -> PEP/Gateway -> Veritas`

Dependency topology is an input to that chain, not an alternate effect path.

## Mesh and infrastructure consequence

A scheduler must not label routes redundant only because they use different logical providers or endpoints. Examples of false redundancy include:

- two providers controlled by the same parent cloud or control plane;
- two regions in the same jurisdiction when jurisdictional independence is required;
- two execution paths using the same authority source or credential issuer;
- separate workers that converge on the same PEP or gateway;
- nominally separate paths with the same physical transit infrastructure;
- separate primary paths that depend on the same recovery or repair mechanism.

This applies equally to cable routes, cloud/mesh compute, model routing, agent execution, credential infrastructure, and recovery design.
