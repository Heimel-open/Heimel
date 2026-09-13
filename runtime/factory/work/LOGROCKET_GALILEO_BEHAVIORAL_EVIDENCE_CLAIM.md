# LogRocket Galileo Behavioral Evidence Claim

Repo: `nsolland/valo-factory`
Canonical base SHA: `745700e7661783ac7a1b72a6f71b637e039f7b7a`
Branch: `feat/logrocket-galileo-behavioral-evidence`
Owner: `nsolland`

Active delivery: bind LogRocket Galileo Funnel Insights to the shared Behavioral Evidence Loop without duplicate evidence, candidate, authority or outcome contracts.

Owned files:
- `connectors/logrocket/*`
- `tests/test_logrocket_galileo_adapter.py`
- `docs/architecture/logrocket-galileo-behavioral-evidence.md`
- `work/LOGROCKET_GALILEO_BEHAVIORAL_EVIDENCE_CLAIM.md`

Dependencies:
- `lib/behavioral_evidence_loop.py`
- Factory evaluation path
- reht for consequence-bearing authorization
- external execution PEP
- Veritas execution receipt

Acceptance:
- Galileo evidence carries privacy/provenance binding through the shared contract.
- Galileo-generated explanations remain derived claims, not truth.
- Adapter may analyze and propose build orders only.
- Merge/deploy/production mutation remain forbidden to the adapter.
- Consequential external candidates route to reht.
- Outcome evidence must bind exact candidate, action digest, authorization and Veritas-backed execution receipt.
- Missing post-execution evidence yields `INSUFFICIENT_EVIDENCE`.
