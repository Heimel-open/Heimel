# Insurable Capability Route v0

This v0 makes an executed capability route mechanically assessable for residual risk without pretending to make an insurer decision.

The executable chain is:

`intent/workspace -> admissible compute route -> consequence-time REHT authorization -> effect -> verified receipt -> deterministic risk signal`

A route is `NOT_ASSESSABLE` unless all of these are present:

- the underlying route passed its admissibility checks;
- the consequence was authorized;
- authority was fresh at consequence time;
- a verified execution receipt exists;
- the consequence is bounded;
- authoritative state integrity is verified.

Only after those gates pass does v0 emit a risk score/band. The current factors are deliberately simple and deterministic: provider trust domain, bounded consequence size and replayability. They are not actuarial weights and must not be represented as an insurance premium or coverage decision.

The output contract explicitly marks itself `SIGNAL_ONLY` and `insurer_decision=false`.

## Demonstrator

`examples/demonstrator_8_insurable_capability_route_v0.py` runs the existing Personal Compute v0 demonstrator first. That path already performs route admission, consequence-time REHT evaluation, effect execution, receipt signing/verification, append-only evidence and restart integrity verification. Demonstrator 8 then seals those execution facts into `InsurableRouteEvidence` and produces the residual-risk signal.

The current reference route uses an external provider and a bounded consequence, is replayable, has verified state integrity and therefore produces an `ASSESSABLE` result with a low deterministic signal. Removing fresh authority or the consequence bound produces `NOT_ASSESSABLE` rather than a higher-but-still-priced score.

## What v0 proves

The relevant market primitive is not only model or provider selection. A route can carry execution evidence sufficient for an external risk actor to decide whether it is even eligible for pricing.

This creates a clean future boundary for underwriters: replace the placeholder signal weights with externally defined underwriting requirements without changing who owns authority or execution truth.

## Explicit non-goals

v0 does not provide insurer pricing, coverage, legal liability allocation, actuarial calibration, payment settlement, provider reputation feeds or insurer-specific policy language.
