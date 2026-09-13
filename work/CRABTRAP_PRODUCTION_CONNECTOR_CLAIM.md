# CrabTrap production connector claim

- Repo: `nsolland/valo-factory`
- Canonical base SHA: `02128accb707c5109dd59ee190ed1f6c5f63d56e`
- Branch: `feat/crabtrap-production-connector`
- Owner: `nsolland`
- Active delivery: pre-forward governed authorization, byte-bound forwarding and response inspection for CrabTrap-compatible HTTP/HTTPS transport
- Owned files:
  - `bin/valo-egress-gate`
  - `bin/valo-response-inspector`
  - `connectors/crabtrap/*`
  - `tests/test_egress_gate.py`
  - `tests/test_response_inspector.py`
  - `schemas/governed_egress_response.schema.json`
  - `docs/architecture/governed-egress-protocol.md`
  - `.github/workflows/ci.yml`
- Dependencies:
  - upstream CrabTrap commit `ac871ccc4460249f71cfc8b55ae4ba6130351b74`
  - VAIG, REHT and RACS artifacts bound to the canonical request digest
- Scope rule: no upstream LLM or static allow decision may authorize forwarding.
