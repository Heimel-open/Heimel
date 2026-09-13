# Aurora-Lens Phase 0 runtime acceptance evidence — 11 August 2026

Title: Aurora-Lens Phase 0 runtime acceptance evidence — 11 August 2026
Author: Njål Solland
Original IP owner: Margaret Stokes for transferred Aurora-Lens artefacts; this evidence record does not alter ownership
Contributors: OpenAI coding assistance under Njål's direction
Status: draft
Based on: Phase 0 transfer package received 11 August 2026
Changes from prior version: initial acceptance record
Permitted use: internal Phase 0 verification and joint review
Related synthesis: `EXTERNAL_ADAPTER_CONTRACT_V0_1.md`

Content type: KRITIKK / verification evidence

## Transferred artefacts verified

Observed SHA-256:

- `aurora_lens-3.0.1-py3-none-any.whl`: `d078f5340c177a894cde2fdb4a317226cb1c4c03e6f55de3e5f9f5cbfe62a3c6`
- `aurora_lens-3.0.1-full-test-suite.zip`: `0702bfcfe0f53e2619acddaad2d4b3aa028afee4503aec1d0d15b0a4175187d0`

The wheel metadata identifies Aurora-Lens 3.0.1 as proprietary and requires Python `>=3.12,<3.13`.

## Observable implementation boundary

The wheel contains the Aurora-Lens runtime, including Lens orchestration, Governor/governance modules, OpenAI/Anthropic upstream adapters, an OpenAI-compatible proxy, audit/forensic surfaces, corpus/evidence components, state-native engine and operator UI assets.

The OpenAI-compatible response formatter returns governance metadata under the top-level `aurora` object and exposes the native governance action vocabulary required by the external reference client.

## Test-suite compatibility finding

A direct smoke run was attempted against the transferred wheel and transferred test suite using the available verification host.

The suite failed during fixture setup before the selected Lens/proxy tests could execute because `tests/tests/conftest.py` imports `PUBLIC_DEMO_EDGE_PATHS` from `aurora_lens.proxy.app`, while that symbol is absent from the transferred v3.0.1 wheel.

Observed failure:

`ImportError: cannot import name 'PUBLIC_DEMO_EDGE_PATHS' from 'aurora_lens.proxy.app'`

Repository search of the extracted wheel found no definition of `PUBLIC_DEMO_EDGE_PATHS`; the transferred test suite references it in `conftest.py`.

This means the hashes verify transfer integrity, but the supplied full test-suite package is not presently a clean executable acceptance suite for the supplied v3.0.1 wheel as delivered.

## Environment qualification

The available verification host is Python 3.13.5, while the wheel explicitly requires Python 3.12.x. The import mismatch above is independent of that version constraint because it is a missing exported symbol in the transferred wheel, but full acceptance must still be repeated on a Python 3.12 environment.

## Independent external adapter harness

The independently written external client/conformance harness currently has four local tests green:

- preserves `PASS`;
- preserves `HARD_STOP`;
- fails closed when the `aurora` governance block is missing;
- fails closed on an unknown governance outcome.

These tests validate the adapter boundary only. They do not substitute for Margaret's Aurora-Lens runtime suite.

## Actual blocker

For full Phase 0 runtime acceptance, the transferred test suite and v3.0.1 wheel need one compatible pair, followed by execution on Python 3.12. This is an acceptance-evidence issue, not a reason to place Aurora-Lens inside VALO or to alter Aurora-Lens policy in the external adapter.
