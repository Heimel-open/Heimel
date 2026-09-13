# VALO 2.0 Governed Workspace — implementation and review handoff

Status snapshot: 2026-08-12. This document is the continuation map for
developers, security reviewers and architecture owners. GitHub PR state and CI
remain the operational source of truth when they differ from this snapshot.

## Architectural decision

VALO governance is centered on the bounded world in which work occurs, not on
the identity or internals of one worker.

```text
candidate information
  -> VALO-owned deterministic state admission
  -> maintained authoritative governed representation
  -> purpose/scope/capability-bounded Governed Workspace
  -> replaceable and untrusted worker
  -> deterministic candidate conformance
  -> fresh sealed Kernel execution context
  -> REHT authorization
  -> RACS contract
  -> Gateway execution
  -> Veritas observation
```

The architectural object is **Governed Operational Reality**: the
organization's current, evidence-backed and policy-governed representation. It
is not a claim of objective or universal truth. The product category used in
this work is **Governed Reality Execution Infrastructure**. The execution
promise is: **work and execute from governed enterprise reality, not the
model's imagined reality**.

## Non-negotiable ownership boundaries

| Component | Owns | Must not claim |
|---|---|---|
| Kernel | provider-neutral state admission, maintained governed state, projection, dependencies, conformance, fresh context origin | objective truth, external authorization or execution |
| Function Fabric | compiled purpose-bound workspace programs | truth, authority or clearance |
| Worker | reasoning and candidate output inside one workspace | trusted state or authority |
| REHT | fresh exact-action admissibility and positive clearance | state ownership or execution |
| RACS | canonical wire contracts, bindings and signatures | runtime policy decisions |
| Gateway | exact permit enforcement and external invocation | semantic truth or authorization |
| Veritas | observed execution/effect evidence and immutable provenance | retroactive authority or truth creation |

## External adapters, never VALO dependencies

- **Margaret / Aurora-Lens** may implement the provider-neutral admission
  assessment contract. Its result is evidence presented to VALO admission, not
  an admission decision. VALO remains fully operable without it. A tenant may
  explicitly require that provider for one class of material; absence then
  holds only that material.
- **Margaret / PEF** is a separate, optional worker-facing cognitive-frame
  adapter. It may render active present, labelled reconstruction, labelled
  projection and relational evaluation inside a workspace. It is not required
  to compile, use or conform a Governed Workspace.
- **Elsa / Authority Instrumentation** may be an external authority-evidence
  adapter. It can supply structured observations about mandate, scope, time and
  revocation. It cannot create Kernel authority or REHT clearance, and its
  absence cannot stop native authority evaluation unless tenant policy
  explicitly requires its evidence for one decision.
- **Jasper / IAB** has no owned normative contract in the available source set.
  It therefore has no normative runtime placement. A later adapter must use a
  provider-neutral VALO contract and cannot become a platform dependency.

These names identify possible adapters, not architectural components. The core
runtime dependency graph is VALO contracts and services only.

The shared owner-review proposal is issue #5 and draft PR #6 in
`nsolland/valo-research-collaborations`. It changes no Margaret- or Elsa-owned
source and creates no approval, licence, state, authority or runtime behavior.

## Revision map

| Repository | Change | State at snapshot |
|---|---|---|
| `nsolland/valo-kernel#19` (issue #18) | VALO-owned provider-neutral state-admission boundary and workspace standing dependencies | HIGH draft; implementation commit `c90164a2ece3834f68243d1e9b38f7d31b8b084b` passed local gates and hosted CI run `31594080198` |
| `nsolland/valo-kernel` | Company Brain boundary, Governed Workspace v1, program lineage, temporal/tenant binding, purpose-bounded expiry | merged through main `7d4afbfbf0da7de540e5d8202235d2cbfcb0df14` |
| `nsolland/valo-kernel#15` (issue #14) | cryptographic Kernel execution-context origin proof | HIGH draft; implementation head `d932825742e95621ff6032826721e0d5233f9ae1` passed hosted CI |
| `nsolland/valo-kernel#17` (issue #16) | Margaret PEF / Governed Workspace boundary | HIGH architecture draft; docs-only head `c51f530e4b62fd42b7d05660f0441f3428f17a00` passed hosted CI; Margaret review pending |
| `nsolland/valo-function-fabric#12` | compile purpose/scope/capability program into workspace request | merged as `8a43758e6ce20ef9655348c8ce55e0dedad63028` |
| `nsolland/reht#21` | exact workspace + independently fresh, cryptographically verified Kernel-context clearance | HIGH draft; head `8ae2598bd2694d650d32b40dcbf5fea82a86a595` passed hosted CI |
| `nsolland/Racs#148` | atomic workspace/kernel digest pair in schemas and Python/Rust/TypeScript bindings | HIGH draft, green head `bba7cd2e3cea715a78a4456754c8ab65adcbc833` |
| `nsolland/valo-gateway#18` | enforce exact lineage and expiry before permit consumption/invocation | HIGH draft, green head `c5b5d4e1bb3db950610bea445f2d2853ec1e7402` |
| `nsolland/Veritas#13` | preserve exact lineage in event, ObservationPackage and WORM evidence | HIGH draft, green head `debeb21251baf56626d0ec6cdfc165a7bcb1d865` |
| `nsolland/valo-research-collaborations#6` (issue #5) | shared Margaret/Elsa/PEF boundary revision, review checklist and negative vectors | draft; head `6900913b066f3baf5297651ee55cee48967daf34`; Margaret/Elsa/VALO-owner decisions pending |

No HIGH draft may be self-merged. It needs independent security/architecture
review (G2/G3) and explicit authorized-owner acceptance (G4).

## Verification ledger

Producer checks recorded for the exact implementation heads above are:

| Boundary | GitHub Actions run | Result |
|---|---:|---|
| Kernel State Admission v1 | `31594080198` | pass on implementation commit `c90164a2` |
| Kernel purpose expiry | `31575203914` | pass |
| Kernel context origin proof | `31576840381` | pass on implementation head `d9328257` |
| Kernel PEF boundary | `31576761360` | pass on docs-only head `c51f530e` |
| REHT workspace clearance and origin verifier | `31577451937` | pass on head `8ae2598b` |
| RACS conformance | `31574865209` | pass |
| RACS repository profile | `31574865182` | pass |
| RACS cross-language binding gate | `31574865194` | pass |
| Gateway conformance | `31575257283` | pass |
| Veritas CI | `31574558401` | pass |

Reviewers must inspect the workflow for the current head, not reuse a green
result from an earlier SHA.

## Reproduction commands

From each repository root, create a clean Python 3.11+ environment and run:

```bash
python -m pip install -e ".[dev]"        # Kernel / Function Fabric / Gateway / Veritas
python -m pytest -q
python -m ruff check src tests
python -m compileall -q src tests
```

For REHT use its test extra:

```bash
python -m pip install -e ".[test]"
python -m pytest -q
python -m ruff check --select E,F,I src tests
python -m compileall -q src tests
```

RACS must additionally run its repository-profile check and the shared Python,
Rust and TypeScript canonical-vector/binding gates defined in its workflows.

## Independent review checklist

1. Recompute every workspace, proposed-action, dependency, context, clearance
   and permit digest from canonical content; never trust a transported digest.
2. Confirm the workspace and Kernel-context digest pair is atomic in every RACS
   artifact and absent together on the explicit legacy path.
3. Confirm `PASS`, a worker identity, provider assessment, admission decision
   or Kernel seal creates no authority.
4. Confirm context origin is RFC 8785/Ed25519 verified against an active,
   explicit tenant-bound key before REHT can issue. The seal proves only
   origin and integrity; it proves neither truth nor authority.
5. Confirm REHT obtains authorization time from its own timezone-aware UTC
   clock, rejects stale/future context outside the configured bounds, and
   checks workspace, purpose, authority and trusted-key validity at actual
   authorization time. The signing key must be valid both at Kernel signing
   time and at REHT authorization time.
6. Change authority, purpose, relevant dependency state, external framework
   fingerprint, nonce, tenant, exact payload, target, key, proof time and
   workspace expiry one at a time; every mutation must fail closed.
7. Confirm Gateway checks equality and expiry before permit consumption and
   again immediately before external invocation.
8. Confirm Veritas preserves provenance without classifying a historical
   execution as authorized merely because lineage fields exist.
9. Reproduce the passing real Kernel signer -> REHT verifier fixture, then add
   a current-head fixture through RACS, Gateway and Veritas/WORM.
10. Run the native admission, workspace and authority paths with all external
    adapters absent. Review any optional adapter mapping against its owner
    contract. Do not implement Jasper/IAB from the name alone.

## Merge and continuation order

1. Review and merge the VALO-owned state-admission boundary from issue #18.
2. Review and merge the Kernel origin-proof PR.
3. Review and merge RACS #148 so the canonical transport contract exists.
4. Rebase, review and merge REHT #21 against the merged Kernel contract.
5. Rebase, review and merge Gateway #18 against merged RACS/REHT semantics.
6. Rebase, review and merge Veritas #13 against the merged receipt contract.
7. Pin compatible package versions and add one cross-repository CI matrix owned
   by the integration/runtime repository.

## Work still open

- Provision and rotate production Kernel signing keys through HSM/KMS; define
  revocation distribution and emergency rollover.
- Add current-head end-to-end CI that imports the actual repositories instead
  of only mirrored fixtures.
- Wire REDO, DEFER, STEP_UP, DENY and HALT to explicit operational queues and
  human-review ownership.
- Keep Margaret, Elsa, Jasper and future providers outside the core dependency
  graph. Review an adapter only against a provider-neutral VALO contract and
  its owner-controlled source; do not infer a runtime role from a name.
- Review PR #17 and implement the PEF boundary proposed in issue #16 only after
  independent agreement that Kernel/reht temporal invariants remain intact.
- Instrument token use, model calls, latency, redo rate, conformance failures,
  execution success and energy proxies. Reduced compute is a testable
  hypothesis, not yet a demonstrated outcome.
- Threat-model projection inference, cross-workspace correlation, compromised
  Kernel signers, stale caches and tenant-key misconfiguration.
