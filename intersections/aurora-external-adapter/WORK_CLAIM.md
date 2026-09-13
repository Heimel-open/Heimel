# Aurora-Lens Phase 0 external adapter work claim

Title: Aurora-Lens Phase 0 external adapter work claim
Author: Njål Solland
Original IP owner: Margaret Stokes for Aurora-Lens; Njål Solland / VALO Research for independent adapter/client mapping and conformance harness
Contributors: OpenAI coding assistance under Njål's direction
Status: draft
Based on: Aurora-Lens v3.0.1 Phase 0 transfer package received 11 August 2026; existing collaboration interface profiles
Changes from prior version: establishes active delivery anchor and corrects topology from in-VALO adapter to external optional Aurora-Lens service boundary
Permitted use: internal joint research and Phase 0 implementation under the signed/being-completed transfer terms; no transfer or implied re-licensing of Aurora-Lens proprietary IP
Related synthesis: ../aurora-lens-reht/INTERFACE_PROFILE_V0_1.md

Content type: FELLES SYNTESE / boundary implementation work

## Active delivery

Build and validate a narrow external call boundary for Aurora-Lens without making Aurora-Lens part of VALO.

Topology:

`caller -> external Aurora-Lens service/adapter -> response`

VALO may be one caller, but the adapter is not a VALO runtime component and does not gain VALO authority.

## Working anchor

- Repository: `nsolland/valo-research-collaborations`
- Canonical base SHA: `62d226efab540561699838374ab4aa539b5fd497`
- Branch: `shared/aurora-lens-phase0-adapter-contract`
- Owner/claim: Njål Solland
- Owned files for this delivery: `intersections/aurora-external-adapter/**` plus proposed corrections to the existing Aurora-Lens interface profile
- Dependency: proprietary Aurora-Lens v3.0.1 wheel and transferred test suite remain external licensed artifacts and are not committed here

## Acceptance boundary

The shared repository may contain interface contracts, conformance vectors, reference client/harness code and acceptance evidence. It must not contain the proprietary Aurora-Lens runtime or wheel.
